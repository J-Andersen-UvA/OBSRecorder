import os
from datetime import datetime

def get_save_location(root_folder, folder_name="Recording"):
    """Sets the location to save the recorded files dynamically."""
    if root_folder is None:
        raise ValueError("Root folder must be provided.")

    os.makedirs(root_folder, exist_ok=True)
    
    # Create a date folder under the root folder
    date_folder = os.path.join(root_folder, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_folder, exist_ok=True)

    # Create a subfolder for each recording session with incremental numbers
    session_folder_base = os.path.join(date_folder, folder_name)

    os.makedirs(session_folder_base, exist_ok=True)

    return session_folder_base

# Example usage
if __name__ == "__main__":
    save_path = get_save_location("C:/example/path")
    print(f"Files will be saved to: {save_path}")
