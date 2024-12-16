from flask import Flask, request, render_template, redirect, url_for, jsonify # type: ignore
import os
import hashlib
import subprocess
import shutil
import magic

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
TOOLS_FOLDER = 'tools'
EXTRACTED_FOLDER = 'extracted'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    frameworks = ['Cocos', 'Flutter', 'React Native', 'Cordova', 'Unity']
    actions = ['reflutter app', 'flutter dart objects dump', 'libil2cpp dumper', 'dump using Hermes decompiler', 'cocos file dumper']
    return render_template('index.html', frameworks=frameworks, actions=actions)

@app.route('/process', methods=['POST'])
def process_file():
    try:
        # Step 1: File Upload and Framework Selection
        file = request.files['file']
        framework = request.form['framework']
        action = request.form['action']
        ip_address = request.form.get('ip_address', '')

        # Step 2: File Validation
        file_signature = magic.Magic(mime=True)
        file_type = file_signature.from_buffer(file.read(2048))
        file.seek(0)
        if not file.filename.endswith('.apk') or file_type != 'application/vnd.android.package-archive':
            return jsonify({'error': 'Invalid file format. Only APK files are allowed.'}), 400

        # Create a unique folder using SHA256 hash
        file_hash = hashlib.sha256(file.filename.encode()).hexdigest()
        extracted_path = os.path.join(EXTRACTED_FOLDER, file_hash)
        os.makedirs(extracted_path, exist_ok=True)

        # Save the file to the upload folder
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Step 3: APK Extraction
        apktool_command = f'apktool d -f "{file_path}" -o "{extracted_path}"'
        result = subprocess.run(apktool_command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"APKTool error: {result.stderr}")

        # Step 4: Perform Action
        tool_path = os.path.join(TOOLS_FOLDER, action.replace(" ", "_"))
        output_path = extracted_path
        if action == 'reflutter app':
            if not ip_address:
                return jsonify({'error': 'IP Address and port must be provided for refluter.'}), 400
            command = f'reflutter "{file_path}" {ip_address}'
        elif action == 'flutter dart objects dump':
            libapp_so_path = extracted_path+'/lib/arm64-v8a'
            print(extracted_path , libapp_so_path)
            if not libapp_so_path:
                raise FileNotFoundError("libapp.so not found in the extracted files.")
            tool_path = '/Users/kranthikiran/Desktop/My_tool/tools/blutter-termux/blutter.py'
            command = f'python3 "{tool_path}" "{libapp_so_path}" "{output_path}"'
        elif action == 'dump using Hermes decompiler':
            index_bundle_path = find_file(extracted_path, 'index.android.bundle')
            if not index_bundle_path:
                raise FileNotFoundError("index.android.bundle not found in the extracted files.")
            tool_path = '/Users/kranthikiran/Desktop/My_tool/tools/hermes-dec-main/hbc_decompiler.py'
            command = f'"{tool_path}" "{index_bundle_path}" "{output_path}"'
        else:
            return jsonify({'error': f'Unsupported action: {action}'}), 400

        action_result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if action_result.returncode != 0:
            raise Exception(f"Action error: {action_result.stderr}")

        return render_template('success.html', output=action_result.stdout, extracted_path=extracted_path)

    except Exception as e:
        error_message = str(e)
        return render_template('error.html', error_message=error_message), 500

def find_file(base_path, file_name):
    for root, dirs, files in os.walk(base_path):
        if file_name in files:
            return os.path.join(root, file_name)
    return None

if __name__ == '__main__':
    app.run(debug=True)