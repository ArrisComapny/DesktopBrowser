import json
import os
import shutil


def create_extension_files(proxy: str, path_file: str):
    proxy_host, proxy_port = proxy.split("@")[-1].split(":")

    username, password = proxy.split("@")[0].replace("http://", "").split(":")

    manifest_content = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Authentication",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version": "22.0.0"
    }

    manifest_path = os.path.join(path_file, 'manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest_content, f, indent=4)

    background_js_content = f"""
var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{proxy_host}",
            port: parseInt({proxy_port})
        }},
        bypassList: ["localhost"]
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{username}",
            password: "{password}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);
"""

    background_js_path = os.path.join(path_file, 'background.js')
    with open(background_js_path, 'w') as f:
        f.write(background_js_content)

    shutil.make_archive(os.path.join(path_file, 'proxy_auth_extension'), 'zip', path_file)
