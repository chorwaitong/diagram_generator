from flask import Flask, jsonify, render_template, request, Response, stream_with_context, send_from_directory
import os
import json
import glob
from main import LLMModule, _invoke_paperbanana, getTimeNow , img_dir 
from PaperBananaRenderer import PaperBananaRenderer

app = Flask(__name__)
llm_module = LLMModule()

@app.route('/')
def index():
    sessions = [os.path.basename(f) for f in glob.glob(os.path.join(img_dir, "session_*"))]
    return render_template('index.html', sessions=sessions, caption="", methodology="", blueprint_str="{}", code_str="", image_url="", current_session="", render_mode="diagram")

@app.route('/stop', methods=['POST'])
def stop_generation():
    from main import request_stop_generation
    request_stop_generation()
    return jsonify({"status": "stopped"})

@app.route('/generate', methods=['POST'])
def generate():
    caption = request.form.get('caption')
    methodology = request.form.get('methodology')
    render_mode = request.form.get('render_mode', 'diagram')
    
    def generate_stream():
        for update in _invoke_paperbanana(llm_module, caption, methodology, render_mode=render_mode):
            # Yield data formatted as Server-Sent Events (SSE)
            yield f"data: {json.dumps(update)}\n\n"

    return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')

    
@app.route('/rerender', methods=['POST'])
def rerender():
    session_id = request.form.get('session_id')
    code_str = request.form.get('generated_code')
    blueprint_json_str = request.form.get('blueprint_json')
    
    session_subfolder = os.path.join(img_dir, session_id)
    blueprint_json = json.loads(blueprint_json_str)
    output_filename = os.path.join(session_subfolder, f"paperbanana_{getTimeNow()}_rerender.png")
    exec_json_path = os.path.join(session_subfolder, "exec.json")

    if "digraph" in code_str:
        result = PaperBananaRenderer.render_dot_code(code_str, blueprint_json, output_filename)
    else:
        result = PaperBananaRenderer.execute_matplotlib_code(code_str, output_filename)
        
    image_url = ""
    if result.get("status") == "success":
        image_url = f"/images/{session_id}/{os.path.basename(output_filename)}"

        if os.path.isfile(exec_json_path):
            with open(exec_json_path, "r", encoding="utf-8") as file:
                execution_history = json.load(file)
            excObj = {'trial':'rerender', 'status': 'complete', 'output':output_filename, 'code':code_str}
            execution_history.append(excObj)

            with open(exec_json_path, "w", encoding="utf-8") as f:
                json.dump(execution_history, f, indent=4)

    sessions = [os.path.basename(f) for f in glob.glob(os.path.join(img_dir, "session_*"))]
    return render_template('index.html', sessions=sessions, caption="", methodology="", 
                           blueprint_str=blueprint_json_str, code_str=code_str, image_url=image_url, current_session=session_id, render_mode="diagram")

@app.route('/load_session')
def load_session():
    session_name = request.args.get('session')
    session_subfolder = os.path.join(img_dir, session_name)
    
    caption, methodology, code_str, blueprint_str, image_url = "", "", "", "{}", ""
    
    inputs_path = os.path.join(session_subfolder, "inputs.json")
    exec_json_path = os.path.join(session_subfolder, "exec.json")

    if os.path.exists(inputs_path):
        with open(inputs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            caption = data.get("caption", "")
            methodology = data.get("methodology", "")
            
    bp_path = os.path.join(session_subfolder, "blueprint.json")
    if os.path.exists(bp_path):
        with open(bp_path, "r", encoding="utf-8") as f:
            blueprint_str = f.read()

    if os.path.isfile(exec_json_path):
        with open(exec_json_path, "r", encoding="utf-8") as file:
            execution_history = json.load(file)

        for item in reversed(execution_history):
            if 'code' in item and 'output' in item:
                if os.path.isfile(item['output']):
                    image_url = f"/images/{session_name}/{os.path.basename(item['output'])}"
                    code_str = item['code']
                    break
        
    sessions = [os.path.basename(f) for f in glob.glob(os.path.join(img_dir, "session_*"))]
    return render_template('index.html', sessions=sessions, caption=caption, methodology=methodology, 
                           blueprint_str=blueprint_str, code_str=code_str, image_url=image_url, current_session=session_name, render_mode="diagram")

@app.route('/images/<path:filename>')
def serve_image(filename):
    from flask import send_from_directory
    return send_from_directory(img_dir, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5889)