import os
import subprocess

def create_pdf_from_latex(latex_code, output_dir="output", output_filename="document.pdf"):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Path for the .tex file and PDF file
    tex_file_path = os.path.join(output_dir, "document.tex")
    pdf_file_path = os.path.join(output_dir, output_filename)

    # Write the LaTeX code to a .tex file
    with open(tex_file_path, "w") as tex_file:
        tex_file.write(latex_code)

    # Compile the LaTeX file to PDF using pdflatex
    try:
        subprocess.run(
            ["pdflatex", "-output-directory", output_dir, tex_file_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"PDF created successfully at: {pdf_file_path}")
        os.system(f"open {pdf_file_path}")
    except subprocess.CalledProcessError as e:
        print("Error during PDF creation:")
        print(e.stderr.decode())
        return None

    return pdf_file_path

try:
    latex_code = open("base.tex", "r").read()
except FileNotFoundError:
    print("File not found. Please check the file name and try again.")
    exit()

# Create the PDF
create_pdf_from_latex(latex_code)