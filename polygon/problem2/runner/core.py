import os
import signal
import sys
import time
import threading
import traceback
from datetime import datetime

import subprocess

import resource
from django.conf import settings

from polygon.models import Program
from polygon.problem2.runner.exception import CompileError


class Runner(object):

    def __init__(self, program: Program):
        self.program = program
        now_string = ''.join(filter(lambda x: x.isdigit(), str(datetime.now())))
        self.workspace = os.path.join(settings.REPO_DIR, 'tasks', now_string)
        os.makedirs(self.workspace, exist_ok=True)
        os.chdir(self.workspace)
        self.config = settings.RUNNER_CONFIG[program.lang]
        self.platform = sys.platform
        with open(self.config["code_file"], "w") as code_file_writer:
            code_file_writer.write(program.code)
        try:
            with open("compile.log", "w") as log:
                compile_process = subprocess.run([self.config["compiler_file"]] + self.config["compiler_args"],
                                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=30)
            if compile_process.returncode != 0:
                try:
                    with open("compile.log", "r") as compile_log_reader:
                        compile_log = compile_log_reader.read()
                except FileNotFoundError:
                    compile_log = "Compiler returned non-zero exit code, but nothing reported."
                raise CompileError(compile_log)
        except subprocess.TimeoutExpired:
            raise CompileError("Compilation time limit (30s) is exceeded.")

    def set_resource_limit(self, **kwargs):
        if "max_cpu_time" in kwargs:  # in seconds
            resource.setrlimit(resource.RLIMIT_CPU, (int(kwargs["max_cpu_time"] + 1), int(kwargs["max_cpu_time"] + 1)))
        if self.platform not in ("darwin",) and "max_memory" in kwargs:  # in bytes
            resource.setrlimit(resource.RLIMIT_AS, (int(kwargs["max_memory"] * 2), int(kwargs["max_memory"] * 2)))
            resource.setrlimit(resource.RLIMIT_STACK, (int(kwargs["max_memory"] * 2), int(kwargs["max_memory"] * 2)))
        if "max_output_size" in kwargs:
            resource.setrlimit(resource.RLIMIT_FSIZE, (int(kwargs["max_output_size"]), int(kwargs["max_output_size"])))

    @staticmethod
    def try_to_open_file(*args):
        ret = []
        for foo, mode in args:
            if not foo:
                foo = os.devnull
            ret.append(open(foo, mode))
        return ret

    def run(self, args=list(), stdin=None, stdout=None, stderr=None, max_time=1, max_memory=256, max_output_size=256):
        os.chdir(self.workspace)
        child_pid = os.fork()

        max_memory = max_memory * 1024 * 1204
        max_output_size = max_output_size * 1024 * 1024
        max_real_time = max_time * 2
        stdin, stdout, stderr = self.try_to_open_file((stdin, "r"), (stdout, "w"), (stderr, "w"))

        if child_pid == 0:
            # in the child now
            try:
                os.setpgrp()
                self.set_resource_limit(max_time=max_time, max_memory=max_memory, max_output_size=max_output_size)
                os.dup2(stdin.fileno(), 0)
                os.dup2(stdout.fileno(), 1)
                os.dup2(stderr.fileno(), 2)
                os.execve(self.config["execute_file"],
                          [self.config["execute_file"]] + self.config.get("execute_args", []) + args, {})
            except:
                traceback.print_exc()
                os._exit(-777)  # Magic number, indicates something wrong during execution
        else:
            print(child_pid)
            killer = threading.Timer(max_real_time, os.killpg, (child_pid, signal.SIGKILL))
            killer.start()

            start_time = time.time()
            pid, status, rusage = os.wait4(child_pid, os.WSTOPPED)
            stop_time = time.time()
            real_time_consumed = stop_time - start_time

            if killer: killer.cancel()

            result = {"time": rusage.ru_utime,
                      "memory": round(rusage.ru_maxrss / 1024),
                      "exit_code": os.WEXITSTATUS(status),
                      "signal": os.WTERMSIG(status) if os.WIFSIGNALED(status) else 0,
                      "verdict": "OK"}

            if result["exit_code"] != 0:
                result["verdict"] = "RUNTIME_ERROR"
            if result["exit_code"] == -777:  # Magic number, see above
                result["verdict"] = "SYSTEM_ERROR"
            elif self.platform not in ("darwin", ) and result["memory"] * 1048576 > max_memory:
                result["verdict"] = "MEMORY_LIMIT"
            elif result["time"] > max_time:
                result["verdict"] = "TIME_LIMIT"
            elif real_time_consumed > max_real_time:
                result["verdict"] = "IDLENESS_LIMIT"
            elif result["signal"] != 0:
                if result["signal"] == signal.SIGUSR1:
                    result["verdict"] = "SYSTEM_ERROR"
                else: result["verdict"] = "RUNTIME_ERROR"
            stdin.close()
            stdout.close()
            stderr.close()
            return result
