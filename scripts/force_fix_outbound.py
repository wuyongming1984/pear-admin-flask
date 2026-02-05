
import os

target_file = r"d:\pear_admin\pear-admin-flask\templates\material\outbound.html"
bad_string = "{ { p.id | tojson | safe } }"
good_string = "{{ p.id | tojson | safe }}"
bad_string_2 = "{ { p.project_name | tojson | safe } }"
good_string_2 = "{{ p.project_name | tojson | safe }}"

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if bad_string not in content:
        print("Target string not found! Maybe it's already fixed?")
        # Check if good string is there
        if "id: {{ p.id" in content:
             print("File appears to be already fixed.")
        else:
             print("File state is unknown.")
             print("Snippet around line 224:")
             lines = content.splitlines()
             if len(lines) > 223:
                 print(lines[223])
    else:
        new_content = content.replace(bad_string, good_string).replace(bad_string_2, good_string_2)
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print("Successfully overwrote file.")
        
        # Verify
        with open(target_file, 'r', encoding='utf-8') as f:
            check = f.read()
            if good_string in check and bad_string not in check:
                print("Verification successful: File is fixed.")
            else:
                print("Verification FAILED: File still has old content.")

except Exception as e:
    print(f"Error: {e}")
