#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Serve deepsec-papers over HTTP on 127.0.0.1 only (not exposed externally).

Prints a single line: the http URL for the given HTML file.
Reuses an existing listener on the preferred port when possible.

Compatible with Python 2.7+ and Python 3.x (stdlib only).
"""
from __future__ import absolute_import, division, print_function

import argparse
import io
import os
import socket
import subprocess
import sys
import time

DEFAULT_PORT = 8765
PID_FILE_NAME = ".deepsec-paper-server.pid"
BIND_HOST = "127.0.0.1"
PY2 = sys.version_info[0] < 3

if PY2:
    import urllib2 as urlreq
else:
    import urllib.request as urlreq


def port_open(port, host=BIND_HOST):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def find_free_port(start, host=BIND_HOST):
    for port in range(start, start + 20):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return port
        except (OSError, socket.error):
            continue
        finally:
            s.close()
    raise RuntimeError("No free local port found")


def http_ok(url):
    try:
        if PY2:
            resp = urlreq.urlopen(url, timeout=1.5)
            try:
                code = getattr(resp, "code", 200) or 200
                return 200 <= int(code) < 500
            finally:
                resp.close()
        else:
            resp = urlreq.urlopen(url, timeout=1.5)
            try:
                code = getattr(resp, "status", None) or resp.getcode()
                return 200 <= int(code) < 500
            finally:
                resp.close()
    except Exception:
        return False


def read_pid(pid_file):
    try:
        if PY2:
            with io.open(pid_file, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        with open(pid_file, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def write_pid(pid_file, pid):
    if PY2:
        with io.open(pid_file, "w", encoding="utf-8") as f:
            f.write(u"{0}".format(pid))
    else:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(pid))


def unlink_quiet(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _popen_kwargs():
    kwargs = {}
    if PY2:
        kwargs["preexec_fn"] = os.setsid
    else:
        kwargs["start_new_session"] = True
    return kwargs


def start_server(root, port, pid_file):
    log_path = os.path.join(root, ".deepsec-paper-server.log")
    log_f = open(log_path, "ab", buffering=0)

    # Bind ONLY to loopback — never 0.0.0.0
    # Py3: python -m http.server --bind 127.0.0.1
    # Py2: tiny inline BaseHTTPServer bound to 127.0.0.1
    if PY2:
        launcher = (
            "import os,sys;"
            "os.chdir({root!r});"
            "from BaseHTTPServer import HTTPServer;"
            "from SimpleHTTPServer import SimpleHTTPRequestHandler;"
            "HTTPServer(({host!r},{port}), SimpleHTTPRequestHandler).serve_forever()"
        ).format(root=root, host=BIND_HOST, port=int(port))
        cmd = [sys.executable, "-c", launcher]
    else:
        cmd = [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            BIND_HOST,
        ]

    proc = subprocess.Popen(
        cmd,
        cwd=root,
        stdout=log_f,
        stderr=log_f,
        **_popen_kwargs()
    )
    write_pid(pid_file, proc.pid)
    for _ in range(30):
        if port_open(port):
            return
        if proc.poll() is not None:
            raise RuntimeError("http.server exited early; see {0}".format(log_path))
        time.sleep(0.1)
    raise RuntimeError(
        "http.server failed to bind {0}:{1}; see {2}".format(BIND_HOST, port, log_path)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Serve HTML report on 127.0.0.1 only and print http URL"
    )
    parser.add_argument("html", help="Path to .html report")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--root", default="", help="Directory to serve (default: html parent)")
    args = parser.parse_args(argv)

    html_path = os.path.abspath(args.html)
    if not os.path.isfile(html_path):
        print("HTML not found: {0}".format(html_path), file=sys.stderr)
        return 1

    root = os.path.abspath(args.root) if args.root else os.path.dirname(html_path)
    try:
        rel = os.path.relpath(html_path, root)
    except ValueError:
        print("HTML must be under serve root {0}".format(root), file=sys.stderr)
        return 1
    if rel.startswith(".."):
        print("HTML must be under serve root {0}".format(root), file=sys.stderr)
        return 1
    rel_url = rel.replace(os.sep, "/")

    pid_file = os.path.join(root, PID_FILE_NAME)
    port = args.port
    need_start = True

    if port_open(port):
        probe = "http://{0}:{1}/{2}".format(BIND_HOST, port, rel_url)
        if http_ok(probe):
            need_start = False
        else:
            port = find_free_port(port + 1)
            need_start = True

    if need_start:
        old = read_pid(pid_file)
        if old and not port_open(port):
            try:
                os.kill(old, 0)
            except OSError:
                unlink_quiet(pid_file)
        start_server(root, port, pid_file)

    url = "http://{0}:{1}/{2}".format(BIND_HOST, port, rel_url)
    for _ in range(20):
        if http_ok(url):
            print(url)
            return 0
        time.sleep(0.1)
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
