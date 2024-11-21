def parse_receivers_file(file_path):
    """
    Parse a file containing email addresses in "Full Name <email@domain.com>" format.
    Lines not matching this format are ignored.
    """
    receivers = []
    if not file_path:
        return receivers
        
    with open(file_path, 'r') as file:
        for line in file:
            if "<" in line and ">" in line:
                receivers.append(line.split("<")[1].split(">")[0].strip())
    return receivers

def read_html_content(file_path):
    """
    Read HTML content from a file.
    """
    with open(file_path, 'r') as file:
        return file.read()
