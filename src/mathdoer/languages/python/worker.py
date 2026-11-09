"""Worker for Python prompts. Run by file path with any Python 3.11 or later interpreter.

Standard library only: this file must not import mathdoer, because the interpreter that
runs it need not have mathdoer installed. The protocol is described in mathdoer.running.
"""
import ast
import builtins
import io
import json
import linecache
import os
import sys
import threading
import traceback

# These must match the constants of the same names in mathdoer.running; a test checks it.
EXIT_CODE_COMPLETED = 0
EXIT_CODE_PROMPT_ERROR = 1
EXIT_CODE_STARTUP_ERROR = 2
MESSAGE_KIND_KEY = "kind"
MESSAGE_TEXT_KEY = "text"
MESSAGE_KIND_OUTPUT = "output"
MESSAGE_KIND_ERROR = "error"
REQUEST_PROMPT_TEXT_KEY = "prompt_text"
REQUEST_STARTUP_PATH_KEY = "startup_path"

EXIT_CODE_APPLICATION_GONE = 3
PROMPT_FILE_NAME = "<prompt>"

send_lock = threading.Lock()


def send_message(protocol_stream, kind, text):
    line = json.dumps({MESSAGE_KIND_KEY: kind, MESSAGE_TEXT_KEY: text}) + "\n"
    with send_lock:
        try:
            protocol_stream.write(line)
            protocol_stream.flush()
        except OSError:
            os._exit(EXIT_CODE_APPLICATION_GONE)  # nobody is listening any more


class MessageWriter(io.TextIOBase):
    """Replaces sys.stdout and sys.stderr: every write becomes one protocol message."""

    encoding = "utf-8"

    def __init__(self, protocol_stream, kind):
        super().__init__()
        self.protocol_stream = protocol_stream
        self.kind = kind

    def writable(self):
        return True

    def write(self, text):
        if not isinstance(text, str):
            raise TypeError(f"write() argument must be str, not {type(text).__name__}")
        if text:
            send_message(self.protocol_stream, self.kind, text)
        return len(text)

    def flush(self):
        pass


def unsupported_input(prompt=""):
    raise RuntimeError("input() is not supported in mathdoer yet: there is nowhere to type a reply")


def remove_worker_folder_from_import_path():
    """Put the working directory last, so the user's modules import but cannot shadow the standard library."""
    worker_folder = os.path.normcase(os.path.dirname(os.path.abspath(__file__)))
    sys.path[:] = [
        entry for entry in sys.path if os.path.normcase(os.path.abspath(entry or ".")) != worker_folder
    ]
    sys.path.append(os.getcwd())


def open_protocol_stream():
    """Keep the original standard output for protocol messages, and send any stray writes
    to standard error instead, so they cannot corrupt a message."""
    protocol_descriptor = os.dup(1)
    os.dup2(2, 1)
    # On Windows a child process still inherits the original handle, so its text reaches
    # the application as lines that are not messages; the application shows those as errors.
    return os.fdopen(protocol_descriptor, "w", encoding="ascii", newline="\n")


def without_worker_frames(traceback_entry):
    while traceback_entry is not None and traceback_entry.tb_frame.f_code.co_filename == __file__:
        traceback_entry = traceback_entry.tb_next
    return traceback_entry


def write_error(heading, error):
    shown_traceback = without_worker_frames(error.__traceback__)
    text = "".join(traceback.format_exception(type(error), error, shown_traceback))
    sys.stderr.write(heading + text)


def report_system_exit(stop):
    if stop.code is not None and not isinstance(stop.code, int):
        print(stop.code, file=sys.stderr)


def split_off_last_expression(tree):
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        return ast.Expression(tree.body.pop().value)
    return None


def run_startup_file(startup_path, namespace):
    """Return an exit code if the run must stop here, otherwise None."""
    try:
        with open(startup_path, encoding="utf-8") as startup_file:
            source = startup_file.read()
        exec(compile(source, startup_path, "exec"), namespace)
    except SystemExit as stop:
        report_system_exit(stop)
        return EXIT_CODE_COMPLETED
    except BaseException as error:
        write_error("Error in the startup file:\n", error)
        return EXIT_CODE_STARTUP_ERROR
    return None


def run_prompt(source, namespace):
    # Lets tracebacks show the prompt's own lines.
    linecache.cache[PROMPT_FILE_NAME] = (len(source), None, source.splitlines(True), PROMPT_FILE_NAME)
    try:
        tree = ast.parse(source, PROMPT_FILE_NAME, "exec")
        last_expression = split_off_last_expression(tree)
        exec(compile(tree, PROMPT_FILE_NAME, "exec"), namespace)
        if last_expression is not None:
            value = eval(compile(last_expression, PROMPT_FILE_NAME, "eval"), namespace)
            if value is not None:
                print(repr(value))
    except SystemExit as stop:
        report_system_exit(stop)
    except BaseException as error:
        write_error("", error)
        return EXIT_CODE_PROMPT_ERROR
    return EXIT_CODE_COMPLETED


def main():
    remove_worker_folder_from_import_path()
    request = json.loads(sys.stdin.readline())
    protocol_stream = open_protocol_stream()
    sys.stdin = io.StringIO("")
    sys.stdout = MessageWriter(protocol_stream, MESSAGE_KIND_OUTPUT)
    sys.stderr = MessageWriter(protocol_stream, MESSAGE_KIND_ERROR)
    builtins.input = unsupported_input

    namespace = {"__name__": "__main__"}
    exit_code = run_startup_file(request[REQUEST_STARTUP_PATH_KEY], namespace)
    if exit_code is None:
        exit_code = run_prompt(request[REQUEST_PROMPT_TEXT_KEY], namespace)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
