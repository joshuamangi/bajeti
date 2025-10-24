from css_html_js_minify import process_single_css_file, process_single_js_file, process_single_html_file
import os

# Define directories
STATIC_DIR = "app/static"
TEMPLATES_DIR = "app/templates"


def minify_static_files():
    # Minify all CSS and JS in /static
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            path = os.path.join(root, file)
            if file.endswith(".css"):
                print(f"Minifying CSS: {path}")
                process_single_css_file(path, overwrite=True)
            elif file.endswith(".js"):
                print(f"Minifying JS: {path}")
                process_single_js_file(path, overwrite=True)

    # Minify all Jinja templates (HTML) in /templates
    for root, _, files in os.walk(TEMPLATES_DIR):
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                print(f"Minifying HTML: {path}")
                process_single_html_file(path, overwrite=True)


if __name__ == "__main__":
    minify_static_files()
