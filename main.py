import base64
import hashlib
import json
import os
import re
import time
import traceback

MODEL_BAME = "gemini-2.5-flash-lite"
script_dir = os.path.dirname(os.path.realpath(__file__))
img_dir = f"{script_dir}\\images\\"
_stop_generation_requested = False

def get_session_subfolder(caption, methodology_text):
    # Create a safe, short hash folder name from the caption text
    capandmethod = caption + methodology_text
    slug1 = hashlib.md5(capandmethod.encode('utf-8')).hexdigest()[:10]
    clean_caption = re.sub(r'[^\w\s-]', '', caption).strip()
    slug2 = re.sub(r'[-\s]+', '_', clean_caption)[:50] # Limits length to roughly 3 visual lines / short phrase
    if not slug2:
        slug2 = "untitled_session"

    session_dir = os.path.join(img_dir, f"session_{slug1}_{slug2}")
    os.makedirs(session_dir, exist_ok=True)
    return session_dir

def getTimeNow():
    return time.strftime("%Y%m%dT%H%M%SZ")

def _prompt_paperbanana_structure(caption, methodology_text):
    return f"""
        You are an expert AI academic illustrator and systems architect following PaperBanana standards.
        Analyze the methodology and return a SINGLE valid JSON object with EXACTLY these keys:
        
        - "layout_description": A detailed spatial arrangement description specifying the hierarchical flow (e.g., top-to-bottom multi-tier architecture).
        - "components": A list of distinct modules. Each module must include:
            - "id": A unique short string identifier (e.g., "soft_sensor", "robust_control").
            - "name": Module title (clean, publication-ready).
            - "function": Primary role or mathematical description.
            - "tier": Integer representing the vertical layer order (1 for top/foundational layer, increasing downwards).
            - "connects_to": A list of component IDs that this module feeds data into (to define precise arrow paths).
            - "icon_suggestion": MANDATORY. A descriptive visual spec for an infographic icon to represent this module (e.g., "gear symbol for optimization", "wave pulse graph for soft sensors", "shield icon for robustness", or "database cylinder for data storage"). CANNOT BE NULL OR EMPTY.
            - "shape_style": Recommended Graphviz node shape or layout badge (e.g., "box", "Mrecord", "component", "ellipse").
        - "color_palette": Academic hex codes tailored for scientific journals (e.g., dictionary with keys like "primary", "secondary", "accent", "background").
        - "canvas_layout_hints": Grid dimensions or aspect ratio recommendations (e.g., width=8, height=10), as well as the size of the layout (e.g., width=8, height=3) as deemed appropriate for the purpose and readability.
        
        Caption: {caption}
        Methodology: {methodology_text}
    """

def _prompt_paperbanana_dot_coder(blueprint_json):
    return f"""
    You are an expert Graphviz DOT and systems architecture designer.
    Write clean, professional Graphviz DOT code to draw a publication-ready systems architecture diagram based *strictly* on this JSON blueprint:
    
    {json.dumps(blueprint_json, indent=2)}
    
    CRITICAL DOCUMENT SIZING & STYLING RULES:
    1. **Canvas Size Constraints:** Set graph dimensions to fit the content appropriately, within a standard portrait document page, e.g.,:
       `ratio="fill";` or `ratio="auto";`
       `rankdir=TB;`
       `nodesep=0.5;` (Ensure reasonable horizontal spacing).
       `ranksep=0.6;` (Ensure tight, controlled vertical spacing between tiers to eliminate dead space).

    2. **Modern Visual Aesthetics (MANDATORY):**
       - **Rounded Rectangles:** Use `shape=box` combined with `style="filled, rounded"` on nodes to achieve smooth, professional rounded corners.
       - **Drop Shadows:** Add a subtle shadow effect to key architectural blocks by setting `style="filled, rounded, dashed"` or utilizing Graphviz node shadow properties where supported, or explicitly applying a soft contrasting drop-shadow color style. Ensure nodes look layered and modern.
       - **Light & Clean Color Palette:** **NEVER** use dark or heavy saturated fills (such as dark green, dark red, or heavy dark solid fills) for node backgrounds. Use crisp, light, elegant pastel or neutral fills (e.g., `#F8F9FA`, `#EBF5FB`, `#F0F4F8`) for node backgrounds, paired with clean dark borders and high-contrast text. Reserve saturated or dark accent colors strictly for key headers, borders, or arrows.

    3. **Strict HTML-Like Label Rules:** If you use HTML-like labels (`label=< ... >`):
       - **NEVER** use HTML entity codes like `²` or unicode superscripts. Write plain text (e.g., write `DR2MPC` or `DR-2MPC` instead of `DR²MPC`).
       - **NEVER** use `STYLE='indent'` or any custom style attributes inside `<TD>` tags. Only use `ALIGN='left'` or `ALIGN='center'` and `COLSPAN`.
       - **NEVER** use `weight="bold"` inside `<font>` tags. Use standard bold tags `<b>...</b>` instead.
       - **ALWAYS** escape ampersands, never use `&` raw but use &amp instead.
       - Ensure all tags are properly closed.
    4. **Academic Styling:** Use the `color_palette` from the blueprint for clean node fills and borders.

    5. **Colors (CRITICAL):** Extract the actual hex codes directly from the blueprint's `color_palette` (e.g., `primary`, `secondary`, `accent`) and use them as literal strings (e.g., `fillcolor="#5C768D"`, `color="#1B365D"`). **NEVER** declare custom global color variables like `primary_color = ...` inside the DOT body.

    6. Keep nodes compact so the flow looks tight and well-proportioned like a standard academic journal figure.

    7. **Output Format:** Return a SINGLE JSON object with key "code" that contains ONLY valid Graphviz DOT code inside a ```dot markdown block. No conversational filler and no comment in the code.
    """

def _prompt_paperbanana_matplot_coder(blueprint_json):
    return f"""
    You are an expert Python scientific illustrator. 
    Write complete, clean, executable Python code using `matplotlib` and `numpy` to draw a professional academic diagram based *strictly* on this JSON blueprint:
    
    {json.dumps(blueprint_json, indent=2)}
    
    CRITICAL GEOMETRIC & LAYOUT INSTRUCTIONS FOR THE CODE:
    1. **Document-Ready Figure Dimensions:** Always initialize the figure width and height to fit standard document columns:
        - For a single column: `fig, ax = plt.subplots(figsize=(3.5, 3.0))` or `(6.0, 4.0)` for standard full-width presentation/thesis blocks, ax.set_xlim(0, 10), ax.set_ylim(0, 10), ax.axis('off').
    2. **Strict Non-Collision Rule:** 
        - If components share the same vertical tier or row, calculate their `x` positions using distinct columns with a mandatory spacing gap so **boxes never overlap horizontally**.
        - Ensure vertical tiers are well-separated (e.g., at least 2.5 units of vertical space between rows).
    3. **Box & Text Containment:** Use `matplotlib.patches.FancyBboxPatch` for containers. Always wrap text (`wrap=True`) and center it with appropriate font sizing (`fontsize=9` to `10`) so text never overflows box borders.
    4. **Safe Primitives Only:** For icons or symbols, use *only* high-level primitives (`Circle`, `Rectangle`) or standard markers. DO NOT use raw `matplotlib.path.Path` arrays.
    5. **Output Format:** Return a SINGLE JSON object with key "code" that contains ONLY executable Python code inside a ```python markdown block. No conversational filler and no comment in the code.
    6. **Print Quality:** Always save figures with `plt.savefig(..., dpi=300, bbox_inches='tight')`
    """

def _prompt_paperbanana_withfixerror(prvprompt, error_code, error_desc):
    errPrompt = f"""
Note that in the previous generation, the following code failed with the following errors, therefore, your responded code should take folowing error/critics in consideration to yield an improved visual.

## Error/ Critics
### Error descriptions / Critics:
{error_desc}
### Broken/Suboptimal code:
{error_code}
"""
    return prvprompt + "\n\n " + errPrompt

def _prompt_paperbanana_critic(blueprint_json, critique_history=""):
    return f"""
    You are an expert academic figure critic and visual QA agent following PaperBanana standards.
    Inspect the provided diagram image against this original blueprint:
    {json.dumps(blueprint_json, indent=2)}
    
    Check for visual and layout defects:
    1. **Text & Overlaps:** Are any text labels overflowing, clipping, or overlapping with boxes/lines?
    2. **Whitespace & Proportions (Crucial):** Is the layout balanced, compact, and professional? Reject the image if there is **excessive vertical dead space, giant empty gaps between tiers, or unnatural stretching**. The diagram must look cohesive and tightly packed like a real journal figure.
    3. **Connection Flow:** Are the arrows clean, direct, and logical without unnecessary clutter?
    4. **Visual appealing"** Does the visual looks appealing and interesting? any infographics used?
           
    If the image is clean, compact, and professional, reply with a SINGLE valid JSON object with: {{"status": "APPROVED", "feedback": "None"}}
    If there are visual defects or excessive whitespace/stretching, reply with a SINGLE valid JSON object with: {{"status": "REJECTED", "feedback": "<detailed instructions to reduce vertical gaps, tighten ranksep, or fix layout compactness>"}}

    Previous Critique History: {critique_history}
    """

def request_stop_generation():
    global _stop_generation_requested
    _stop_generation_requested = True

def _invoke_paperbanana(llm, caption, methodology_text, render_mode="diagram", verbose = False):        
    global _stop_generation_requested
    _stop_generation_requested = False
    try:     
        maxRetries, hasValidStructure, hasValidOutput = 5, False, False
        session_subfolder = get_session_subfolder(caption, methodology_text)
        exec_json_path = os.path.join(session_subfolder, "exec.json")
        img_filename = os.path.join(session_subfolder, f"paperbanana_{getTimeNow()}")
        
        # Save input configuration to JSON in the session subfolder
        inputs_data = {"caption": caption, "methodology": methodology_text, "render_mode": render_mode}
        inputs_path = os.path.join(session_subfolder, "inputs.json")
        with open(inputs_path, "w", encoding="utf-8") as f:
            json.dump(inputs_data, f, indent=4)

        yield {"status": "progress", "message": "Generating structured blueprint..."}
        prompt = _prompt_paperbanana_structure(caption, methodology_text)
        for retry in range(maxRetries):
            if _stop_generation_requested:
                yield {"status": "stopped", "message": "Generation stopped by user."}
                return
            
            print(f"\n\n ============= Paper banana Structure Generation ({retry} of {maxRetries}) ==============")
            promptObj = {'type':'TextReply', 'prompt':prompt}
            response = llm.invoke(promptObj)
            structured_blueprint = safe_parse_llm_json_v2(response)
            if not structured_blueprint:
                errMsg = f"The LLM blueprint returned is None"
                print(errMsg)
                continue

            if 'layout_description' in structured_blueprint and ('components' in structured_blueprint or 'component' in structured_blueprint):
                hasValidStructure = True
                break
            else:
                errMsg = f"The LLM blueprint returned is invalid without the necessary keys, got {structured_blueprint}"
                print(errMsg)
                continue

        if not hasValidStructure:
            print("[X] Paperbanana structure generation loop complete with error")
            yield {"status": "error", "message": "Invalid structure obtained, rendering wont continue."}
            # return {'success':False}    
        else:
            print("[*] Valid structure obtained.")
        
        # Save structured blueprint to JSON
        blueprint_path = os.path.join(session_subfolder, "blueprint.json")
        with open(blueprint_path, "w", encoding="utf-8") as f:
            json.dump(structured_blueprint, f, indent=4)
        yield {
            "status": "blueprint_ready", 
            "blueprint": json.dumps(structured_blueprint, indent=2),
            "session": os.path.basename(session_subfolder)
        }

        execution_history = []
        if os.path.isfile(exec_json_path):
            with open(exec_json_path, "r", encoding="utf-8") as file:
                execution_history = json.load(file)
            print("[*] Loaded execution history from {exec_json_path}")

        maxRetries = 20 # Allow more trials        
        error_code, error_desc,  critique_history= "", "", ""
                  
        from PaperBananaRenderer import PaperBananaRenderer
        code_prompt = _prompt_paperbanana_dot_coder(structured_blueprint) if render_mode == "diagram" else _prompt_paperbanana_matplot_coder(structured_blueprint) 
        prompt = code_prompt
        for retry in range(maxRetries):            
            yield {"status": "progress", "message": f"Rendering iteration {retry + 1}..."}
            print(f"\n\n ============= Paper banana Rendering ({retry} of {maxRetries}) ==============")
            excObj = {'trial':retry, 'status': 'complete with error'}

            if retry>0 and (error_code or error_desc):
                # Meaning error encountered previously....
                prompt = _prompt_paperbanana_withfixerror(code_prompt, error_code, error_desc)
                time.sleep(5)    #Rest a bit between LLM-calls

            promptObj = {'type':'TextReply', 'prompt':prompt}
            response = llm.invoke(promptObj)
            excObj['prompt'] = prompt
            code_response = safe_parse_llm_json_v2(response)
            if not code_response or not 'code' in code_response:
                errMsg = f"The LLM code_response returned is None or is without code key"
                excObj['error'] = errMsg                
                execution_history.append(excObj)
                print(errMsg)
                continue

            output_filename = f"{img_filename}_r{retry}.png"  
            returned_code = code_response['code']
            excObj['output'] = output_filename

            yield {
                "status": "code_ready", 
                "code": returned_code,
                "iteration": retry
            }
            result = PaperBananaRenderer.render_dot_code(returned_code, structured_blueprint, output_filename) if render_mode=="diagram" else PaperBananaRenderer.execute_matplotlib_code(returned_code, output_filename)

            if result.get("status") != "success":
                error_code = returned_code
                error_desc = result.get("error", "Unknown execution failure")
                processed_error_code = result.get("error_code", "")
                errMsg = f"Failed in rendering image: {error_desc} \nProcessed Code:\n{processed_error_code}"  
                excObj['error'] = error_desc
                excObj['code'] = processed_error_code                 
                execution_history.append(excObj)
                print(errMsg)
                continue

            # Convert image to base64 or relative url to stream immediately
            image_url = f"/images/{os.path.basename(session_subfolder)}/{os.path.basename(output_filename)}"
            yield {
                "status": "image_ready",
                "image_url": image_url,
                "iteration": retry
            }

            # CLOSED-LOOP VISUAL INSPECTION (VLM CRITIC AGENT)
            time.sleep(5) # Rest a while before next move...
            print(f"[*] Running Closed-Loop VLM Critic Inspection on generated image {output_filename}")
            if os.path.exists(output_filename):
                with open(output_filename, "rb") as img_file:
                    img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

                # Construct Multimodal Critic Request
                critic_prompt_text = _prompt_paperbanana_critic(structured_blueprint, critique_history)
                promptObj = {'type':'HumanMessage', 'prompt':critic_prompt_text, "mime_type":"image/png", "data":img_base64}
                critic_res = llm.invoke(promptObj)
                critic_data = safe_parse_llm_json_v2(critic_res)
                excObj['code'] = returned_code
                if critic_data and critic_data.get("status") == "APPROVED":
                    print("[SUCCESS] VLM Critic Approved the Diagram!")
                    excObj['status'] = 'Complete, diagram approved by critic'            
                    execution_history.append(excObj)
                    hasValidOutput = True
                    break
                else:
                    feedback = critic_data.get("feedback", "Visual layout defect detected.") if critic_data else "Critic parsing failed."
                    print(f"[CRITIC REJECTED]: {feedback}")
                    yield {"status": "critic_rejected", "feedback": feedback}
                    error_desc = f"Visual QA Defect Detected by Critic: {feedback}"
                    critique_history += f" | Attempt {retry+1} feedback: {feedback}"
                    excObj['status'] = 'Complete, but diagram disapproved'      
                    excObj['error'] = error_desc            
                    execution_history.append(excObj)
                    continue
            else:
                error_code = returned_code
                error_desc = "Render completed but output file missing on disk."
                continue

        

        if hasValidOutput:            
            print("Paperbanana invoking loop complete")
            yield {"status": "success", "output_path": output_filename, "code": returned_code}
            # return {'success':True,
            #         'render_details':
            #             {'output_path': output_filename,
            #             'code': returned_code
            #             }
            #         }
        else:
            yield {"status": "failed", "message": "Max retries reached without approval."}
            # print("Paperbanana invoking loop complete with error")
            # return {'success':False
            #         }            
        
    except Exception as e:
        print(f"Exception while invoking paper banana")
        traceback.print_exc()
        yield {"status": "error", "message": str(e)}
        # return {'error': f"Exception: {e}"}
    finally:
        if execution_history and len(execution_history)>0:            
            with open(exec_json_path, "w", encoding="utf-8") as f:
                json.dump(execution_history, f, indent=4)

def safe_parse_llm_json_v2(response):
    from langchain_core.utils.json import parse_json_markdown
    from json_repair import repair_json
    from langchain_core.messages import AIMessage
    import re
    if isinstance(response, AIMessage):
        text = response.content
    else:
        text = str(response)
        
    try:
        # 1. Try standard parser first
        return parse_json_markdown(text)
    except Exception:
        try:           
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            json_str = match.group(1) if match else text

            # --- FIX INVALID SINGLE-QUOTE ESCAPES ---
            json_str = re.sub(r'\\\\?\'', "'", json_str)
            # -----------------------------------------------------------

            # 3. Aggressive LaTeX & Escape Sanitizer:
            # Any single backslash followed by letters (LaTeX commands like \label, \dot, \begin, etc.) 
            # must be converted into a double backslash (\\) so JSON accepts it as a literal backslash.
            # We look for a backslash NOT preceded by another backslash, followed by letters.
            # sanitized = re.sub(r'(?<!\\)\\([a-zA-Z]+)', r'\\\\\\1', json_str) #not working as it resulted into many \\1
            sanitized = re.sub(r'(?<!\\)\\([a-zA-Z]+)', lambda m: '\\\\' + m.group(1), json_str)

            # 4. Handle any remaining isolated single backslashes (like Windows paths or symbols)
            # that are not valid JSON escape characters (n, r, t, b, f, u, ", \, /)
            sanitized = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', sanitized)
        
            # Parse using the repaired version of json.loads
            repaired_str = repair_json(sanitized)
            return json.loads(repaired_str)
        except Exception as e:
            print(f"Failed to parse or repair JSON: {text[:100]}... Error: {e}")
            if repaired_str:
                print(f"Repaired json str: \n {repaired_str}")
            
            return {"error": "Invalid JSON format", "raw": text}
    
class LLMModule:
    def __init__(self):
        from langchain_core.output_parsers import JsonOutputParser    
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_BAME,
            response_mime_type="application/json",
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

        self.llmTxtOnly = ChatGoogleGenerativeAI(
            model=MODEL_BAME,
            response_mime_type="text/plain",
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

        self.chain = self.llm | JsonOutputParser()
        print(f"LLMModule initialized with model {MODEL_BAME}")

    def invoke(self, res):
        from langchain_core.messages import HumanMessage
        try:
            if 'type' in res and res['type'] == 'TextReply':
                print(f"Invoking LLM with TextReply prompt")
                message = HumanMessage(
                    content=res.get("prompt")
                )
                return self.llmTxtOnly.invoke([message])
            elif 'type' in res and res['type'] == 'HumanMessage':                    
                print(f"Invoking LLM with HumanMessage prompt")
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": res.get("prompt")},
                        {
                            "type": "media",
                            "source_type": "base64",
                            "mime_type": res.get("mime_type", "application/pdf"),
                            "data": res.get("data", res.get("pdf_base64", None))
                        },
                    ]
                )
                return self.chain.invoke([message]) 
            
            else:
                print(f"Invalid request format: {res}")
                return {'error': "Invalid request format"} 
            
            
        except Exception as e:
            # Extract detailed Google API error response if available
            error_details = str(e)
            if hasattr(e, 'response') and e.response:
                try:
                    error_details = e.response.text
                except Exception:
                    pass
            elif hasattr(e, 'body'):
                error_details = str(e.body)

            print(f"Google API Request Details: {error_details}")
            print(f"Request payload was: {res}")
            
            return {'error': f"Error Invoking LLM: {error_details}"}

if __name__ == "__main__":
    # --- TEST SCRIPT FOR PAPERBANANA SYSTEM GENERATION ---
    print("PaperBanana Generation Test...")
    
    # 1. Initialize the LLM Module (ensure GEMINI_API_KEY is set in your environment variables)
    try:
        llm_module = LLMModule()
    except Exception as e:
        print(f"[X] Failed to initialize LLMModule. Check your API key and model name: {e}")
        exit(1)

    # Caption and methodology specification
    caption_text = (
        "A compact, vertical systems-engineering block diagram illustrating the "
        "integrated 3-part research framework for robust and efficient eco-driving control, "
        "optimized for portrait A4 document layout."
    )

    methodology_text = """
        A clean, minimalist, vector-style portrait system block diagram on a pure white background, designed for standard A4 academic thesis documents (compact vertical footprint spanning approx. 1/4 page width/height ratio). Use a professional color palette consisting of navy blue (#1B365D), slate gray (#5C768D), and teal accents (#008080).

        Layout and Structure (Stacked / Vertical Convergence):
        - Vertical Stack Layout: To avoid an excessively wide aspect ratio, stack the three core objective modules in a balanced vertical or two-column staggered arrangement that feeds compactly downward into the final terminal node.
        - Module 1 (Objective O1 - Real-Time Soft Sensor): Compact box with an embedded sensor icon, detailing vehicle mass and road grade estimation (RLM-SMFF & SRAEKF).
        - Module 2 (Objective O2 - Fault-Tolerant Robust Control): Compact box with an embedded robustness/shield icon, detailing the DR²MPC architecture for autonomous platooning.
        - Module 3 (Objective O3 - Machine Learning Optimization): Compact box with an embedded ML/nodes icon, detailing automated cost tuning via SENMPC and bi-level framework.
        - Terminal Node (Bottom): A centered, unified container titled "Robust & Efficient Eco-Driving Control Framework".
        - Integration Flow: Clean, converging arrows flowing from the modules downward into the final control framework.
        - Visual Style: Sharp vector lines, clean container boxes with embedded geometric icons inside each block, legible sans-serif typography, and professional aspect ratio suitable for portrait thesis formatting.
    """

    # 3. Construct the request payload matching your Flask /invoke schema
    test_payload = {
        "type": "PaperBananaRender",
        "prompt": f"Caption: {caption_text}\n\nMethodology:\n{methodology_text}",
        "caption": caption_text
    }

    print("\n[*] Sending request to LLM for code generation and sandbox execution...")
    
    # 4. Invoke the pipeline
    response = _invoke_paperbanana(llm_module, caption_text, methodology_text, render_mode = "diagram", verbose = True)

    # 5. Inspect and verify results
    if isinstance(response, dict):
        print("\n[/] PaperBanana diagram generated successfully!")
        
        render_details = response.get("render_details", {})
        if "output_path" in render_details:
            output_file = render_details["output_path"]
            print(f"[/] Final figure saved to disk at: {os.path.abspath(output_file)}")
            
    else:
        print("\n[X] Generation pipeline encountered an error:")
        print(json.dumps(response, indent=2))


