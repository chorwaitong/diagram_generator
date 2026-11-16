import subprocess
import tempfile
import graphviz
import base64
import os
import re

def sanitize_dot_code(dot_code, blueprint_json):
    if not dot_code:
        return dot_code

    dot_code = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', dot_code)
    
    # # Strip C-style comments (/* ... */) that can break attribute parsing
    # dot_code = re.sub(r'/\*.*?\*/', '', dot_code, flags=re.DOTALL)

    # # 1. Strip invalid global variable assignments
    # dot_code = re.sub(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*"[^"]*"\s*;?', '', dot_code, flags=re.MULTILINE)
    # dot_code = re.sub(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*#[0-9a-fA-F]+\s*;?', '', dot_code, flags=re.MULTILINE)

    # # def escape_html_labels(match):
    # #     label_content = match.group(0)
    # #     # Replace any & not already part of & inside the label block
    # #     return re.sub(r'&(?!\s*amp;)', '&', label_content, flags=re.IGNORECASE)

    # # # Apply the escaper specifically to any content enclosed in label=< ... >
    # # dot_code = re.sub(r'label\s*=<[\s\S]*?>', escape_html_labels, dot_code)
    
    # # # Also catch general unescaped ampersands just in case
    # # dot_code = re.sub(r'&(?!\s*amp;)', '&', dot_code)

    # # 3. Generic Superscript Conversion
    # superscript_map = {
    #     '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
    #     '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    #     '⁺': '+', '⁻': '-', '⁼': '=', '⁽': '(', '⁾': ')',
    #     'ⁿ': 'n', 'ⁱ': 'i'
    # }
    # for sup_char, normal_char in superscript_map.items():
    #     dot_code = dot_code.replace(sup_char, normal_char)
    # dot_code = re.sub(r'<sup>(.*?)</sup>', r'^\1', dot_code, flags=re.IGNORECASE)

    # # 4. Strip invalid STYLE or WEIGHT attributes inside TD or FONT tags (NOT node style defaults)
    # # Be more precise: only target STYLE= inside HTML tags or non-standard places
    # dot_code = re.sub(r'(?i)(<[^>]+)\s+STYLE\s*=\s*[\'"][^\'"]*[\'"]', r'\1', dot_code)

    # # 5. ROBUST COMMAS & BRACKET CLEANUP (Fixes both ,, ,] and [, issues)
    # # Remove leading commas right after opening brackets: [ , attr=val ] -> [ attr=val ]
    # dot_code = re.sub(r'\[\s*,', '[', dot_code)
    # # Remove trailing commas right before closing brackets: [ attr=val, ] -> [ attr=val ]
    # dot_code = re.sub(r',\s*([\]}])', r'\1', dot_code)
    # # Clean up any double commas: ,, -> ,
    # dot_code = re.sub(r',\s*,', ',', dot_code)

    # # 6. Substitute color variable names with hex codes
    # color_palette = blueprint_json.get("color_palette", {})
    # if isinstance(color_palette, dict):
    #     palette_map = {
    #         "primary_color": color_palette.get("primary", "#1B365D"),
    #         "secondary_color": color_palette.get("secondary", "#5C768D"),
    #         "accent_color": color_palette.get("accent", "#008080"),
    #         "background_color": color_palette.get("background", "#FFFFFF"),
    #         "primary": color_palette.get("primary", "#1B365D"),
    #         "secondary": color_palette.get("secondary", "#5C768D"),
    #         "accent": color_palette.get("accent", "#008080")
    #     }
    #     for var_name, hex_val in palette_map.items():
    #         dot_code = re.sub(rf'\b({var_name})\b', f'"{hex_val}"', dot_code)

    # 7. Standardize font names
    dot_code = dot_code.replace('fontname="Helvetica-Neue"', 'fontname="Helvetica"')
    dot_code = dot_code.replace("fontname='Helvetica-Neue'", "fontname='Helvetica'")

    return dot_code

class PaperBananaRenderer:
    @staticmethod
    def render_dot_code(dot_code, blueprint_json, output_path="figure.png"):
        print("[*] Rendering dot code")
        """
        Compiles Graphviz DOT syntax into a publication-quality raster asset (300 DPI).
        Graphviz handles all box positioning, node sizing, and arrow routing automatically.
        """
        # Clean markdown wrappers if present
        if "```dot" in dot_code:
            dot_code = dot_code.split("```dot")[1].split("```")[0].strip()
        elif "```" in dot_code:
            dot_code = dot_code.split("```")[1].split("```")[0].strip()

        # --- Sanitize DOT code programmatically ---
        dot_code = sanitize_dot_code(dot_code, blueprint_json)

        if "digraph" in dot_code:
            # Insert size constraints right after the opening bracket '{' of the digraph
            insertion_point = dot_code.find("{") + 1
            sizing_attributes = '\n    dpi=300;\n    ratio="fill";\n'
            dot_code = dot_code[:insertion_point] + sizing_attributes + dot_code[insertion_point:]

        base_name = output_path.replace(".png", "")
        
        try:
            # Create a Graphviz source object
            g = graphviz.Source(dot_code, format='png')
            # Force strict DPI and sizing parameters for publication print quality

            # Render to file (Graphviz automatically appends .png)
            rendered_file = g.render(filename=base_name, cleanup=True, view=False)
            
            if not os.path.exists(rendered_file):
                return {"error": "Graphviz compilation completed, but no image file was generated."}
            
            with open(rendered_file, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                
            return {
                "status": "success",
                "output_path": rendered_file,
                "image_base64": encoded_string
            }
        except Exception as e:
            return {"error": f"Graphviz rendering failed: {str(e)}", "error_code": dot_code}
        
    @staticmethod
    def execute_matplotlib_code(code_str, output_path="figure.png"):
        print("[*] Executing matplotlib code")
        """
        Safely executes generated matplotlib/diagram code in a temporary environment
        to produce a publication-ready vector-quality raster asset (300 DPI).
        """
        # Strip markdown code blocks if present
        if "```python" in code_str:
            code_str = code_str.split("```python")[1].split("```")[0].strip()
        elif "```" in code_str:
            code_str = code_str.split("```")[1].split("```")[0].strip()
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            wrapped_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# --- Force Standard Document Width/Height Defaults ---
plt.rcParams.update({
    'figure.dpi': 300,
    'font.size': 10
})

# --- PaperBanana Generated Code ---
{code_str}
# ----------------------------------

# Ensure figure is saved properly with publication settings
if 'fig' in locals():
    fig.savefig(r"{output_path}", dpi=300, bbox_inches='tight')
elif plt.get_fignums():
    plt.savefig(r"{output_path}", dpi=300, bbox_inches='tight')
plt.close('all')
"""
            f.write(wrapped_code)
            temp_file_name = f.name

        try:
            # Execute code inside a controlled subprocess sandbox
            result = subprocess.run(
                ["python", temp_file_name],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                return {"error": f"Execution error: {result.stderr}"}
            
            if not os.path.exists(output_path):
                return {"error": "Execution completed, but no figure file was generated."}
            
            with open(output_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                
            return {
                "status": "success",
                "output_path": output_path,
                "image_base64": encoded_string
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out."}
        except Exception as e:
            return {"error": f"Sandbox execution failed: {str(e)}", "error_code": wrapped_code}
        finally:
            if os.path.exists(temp_file_name):
                os.remove(temp_file_name)


# --- TEST SCRIPT ---
if __name__ == "__main__":
    print("Initializing PaperBanana Renderer Unit Test...")
    
    # Sample publication-grade matplotlib code simulation
    script_file_path = "sampleMatplotlibScript.txt"
    with open(script_file_path, "r", encoding="utf-8") as f:
        sample_matplotlib_script = f.read()
    
    test_output_filename = "test_paperbanana_output.png"
    
    # Run the renderer
    result = PaperBananaRenderer.execute_matplotlib_code(sample_matplotlib_script, test_output_filename)
    
    # Verify outputs
    if result.get("status") == "success":
        print("[SUCCESS] Matplotlib script executed cleanly in sandbox!")
        print(f"Generated Asset Path: {result.get('output_path')}")
        print(f"Base64 Payload Length: {len(result.get('image_base64'))} characters")
        
        # Verify file exists on disk
        if os.path.exists(test_output_filename):
            print(f"[VERIFIED] File successfully saved locally at: {os.path.abspath(test_output_filename)}")
            # Optional: Clean up test artifact
            # os.remove(test_output_filename)
    else:
        print("[FAILED] Test encountered an error:")
        print(result.get("error"))