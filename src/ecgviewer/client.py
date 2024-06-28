import webview


def run_client(host, port):
    # Create the webview.
    window = webview.create_window(
        'ECG Viewer',
        f'http://{host}:{port}',
        width=1200,
        height=600,
    )

    # noinspection PyTypeChecker
    webview.start(menu=[
        webview.menu.Menu('File', [
            webview.menu.MenuAction(
                'Load Record...',
                lambda: window.evaluate_js("document.querySelector('#upload-data input').showPicker()")
            ),
            webview.menu.MenuAction(
                'Load Annotations...',
                lambda: window.evaluate_js("document.querySelector('#upload-annotations input').showPicker()")
            ),
        ]),
    ])
