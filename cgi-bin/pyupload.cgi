#!/usr/bin/env python

import cgitb
cgitb.enable()

import cgi
import html
import logging
import os
import pathlib
import socket

REQUEST_METHOD = os.environ.get('REQUEST_METHOD', 'GET')
REQUEST_PORT = os.environ.get("SERVER_PORT", '8000')


def render_form(uploaded=None, not_uploaded=None):
    print("Content-Type: text/html")
    print()
    print("""
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
    """)

    if uploaded:
        print("""
            <h3>Files uploaded successfully:</h3>
            <ul>
        """)
        for fname in uploaded:
            print(f"<li>{html.escape(fname)}</li>")
        print("</ul><hr>")

    if not_uploaded:
        print("""
            <h3>Files not uploaded successfully:</h3>
            <ul>
        """)
        for fname, reason in not_uploaded:
            print(f"<li>{html.escape(fname)} - {html.escape(reason)}</li>")
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
        logging.warning('Skipping generating address QR code, qrcode library not installed or not in python path.')


def sanitize_path(filename):
    if not filename:
        raise ValueError("No filename")

    required_parent_dir = f"{os.path.dirname(__file__)}/../"
    disallowed_dirs = [
        f"{required_parent_dir}cgi-bin",
        f"{required_parent_dir}htbin",
        f"{required_parent_dir}.git",
    ]

    test_results = []
    target = (pathlib.Path(required_parent_dir) / filename).resolve()
    for test_dir in (required_parent_dir, *disallowed_dirs):
        base = pathlib.Path(test_dir).resolve()
        test_results.append(target != base and target.is_relative_to(base))

    if not test_results[0] or any(test_results[1:]):
        raise ValueError("Invalid filename")

    return target.absolute()


if REQUEST_METHOD == "POST":
    form = cgi.FieldStorage()
    files = form['uploadedfile'] if isinstance(form['uploadedfile'], list) else [form['uploadedfile']]

    uploaded = []
    not_uploaded = []
    for file in files:
        filename = file.filename
        try:
            upload_path = sanitize_path(filename)
            logging.info(f"Uploading to '{upload_path}'")

            with open(upload_path, "wb+") as f:
                f.write(file.file.read())

            uploaded.append(filename)
        except ValueError as e:
            not_uploaded.append((filename, e.args[0]))
        except Exception as e:
            logging.error("Failed to upload", exc_info=True)
            not_uploaded.append((filename, "Internal error"))

    render_form(uploaded=uploaded, not_uploaded=not_uploaded)

else:
    render_form()