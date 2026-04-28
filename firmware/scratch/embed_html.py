import os

def embed_html():
    input_path = 'data/index.html'
    output_path = 'main/index_html.h'
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Escape for C string
    escaped = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n"\n"')
    
    header_content = f"""#ifndef INDEX_HTML_H
#define INDEX_HTML_H

static const char INDEX_HTML[] = 
"{escaped}";

#endif
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header_content)
    
    print(f"Successfully generated {output_path}")

if __name__ == "__main__":
    embed_html()
