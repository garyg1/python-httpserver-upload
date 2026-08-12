#!/usr/bin/env python

import cgitb
cgitb.enable()

import cgi
import logging
import os
import html
import socket
import pathlib
import sys

REQUEST_METHOD = os.environ.get("REQUEST_METHOD", "GET")
REQUEST_PORT = os.environ.get("SERVER_PORT", "8000")


def render_form(success_filenames=None, errors=None):
    print("Content-Type: text/html")
    print()
    print("""
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
    """)

    if success_filenames:
        print("""
            <h3>Files uploaded successfully:</h3>
            <ul>
        """)
        for fname in success_filenames:
            print(f"<li>{html.escape(fname)}</li>")
        print("</ul><hr>")

    if errors:
        print("""
            <h3>Files not uploaded successfully:</h3>
            <ul>
        """)
        for fname, failure_reason in errors:
            print(f"<li>{html.escape(fname)} - {html.escape(failure_reason)}</li>")
        print("</ul><hr>")

    print(f"""
        <h2>Upload a file</h2>
        <p>Files will be uploaded to <strong>{os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))}/</strong></p>
    """)

    print(f"""
        <form action="/cgi-bin/pyupload.cgi" method="POST" enctype="multipart/form-data">
            <input type="file" name="uploadedfile" multiple>
            <input type="submit" value="Upload File">
        </form>
    """)

    try:
        import qrcode
        import qrcode.image.svg

        url = f'http://{socket.getfqdn()}.local:{REQUEST_PORT}/cgi-bin/pyupload.cgi'
        qr = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
        print(f"""
            <hr>
            <p>Scan to access on another device: <a href="{url}">{url}</a></p>
            {qr.to_string().decode('utf-8')}
        """)

    except ImportError:
        logging.warning("Skipping generating address QR code, qrcode library not installed or not in python path.")


class PyUploadError(ValueError):
    pass


def sanitize_path(path, required_parent_dir, disallowed_dirs):
    test_results = []
    target = (pathlib.Path(required_parent_dir) / path).resolve()
    for test_dir in (required_parent_dir, *disallowed_dirs):
        base = pathlib.Path(test_dir).resolve()
        test_results.append(target != base and target.is_relative_to(base))

    if not test_results[0] or any(test_results[1:]):
        raise PyUploadError("Invalid path")

    return target.absolute()


if REQUEST_METHOD == "POST":
    form = cgi.FieldStorage()
    files = (
        form["uploadedfile"]
        if isinstance(form["uploadedfile"], list)
        else [form["uploadedfile"]]
    )

    success_filenames = []
    errors = []
    for file in files:
        filename = file.filename
        try:
            if not filename:
                raise PyUploadError("No filename")

            base_dir = f"{os.path.dirname(__file__)}/../"
            upload_path = sanitize_path(
                filename,
                base_dir,
                [f"{base_dir}cgi-bin", f"{base_dir}htbin", f"{base_dir}.git"],
            )
            print(upload_path)
            with open(upload_path, "wb+") as f:
                f.write(file.file.read())

            success_filenames.append(filename)
        except PyUploadError as e:
            errors.append((filename, e.args[0]))
        except Exception as e:
            print("Failed to upload", e, file=sys.stderr)
            errors.append((filename, "Internal error"))

    render_form(success_filenames=success_filenames, errors=errors)

else:
    render_form()
