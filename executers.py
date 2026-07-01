import os
import json
import shutil
import uuid
import difflib


BACKUP_DIR = "backups"
EXECUTION_DIR = "executions"
DIFF_DIR = "diffs"


def create_backup(file_path, execution_id):

    backup_folder = os.path.join(
        BACKUP_DIR,
        execution_id
    )

    os.makedirs(backup_folder, exist_ok=True)

    backup_file = os.path.join(
        backup_folder,
        os.path.basename(file_path)
    )

    shutil.copy2(
        file_path,
        backup_file
    )

    return backup_file


def generate_diff(old_content, new_content):

    return "\n".join(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile="old",
            tofile="new",
            lineterm=""
        )
    )


def save_execution(execution):

    os.makedirs(
        EXECUTION_DIR,
        exist_ok=True
    )

    file_path = os.path.join(
        EXECUTION_DIR,
        f"{execution['execution_id']}.json"
    )

    with open(file_path, "w") as f:
        json.dump(
            execution,
            f,
            indent=2
        )


def load_execution(execution_id):

    file_path = os.path.join(
        EXECUTION_DIR,
        f"{execution_id}.json"
    )

    with open(file_path) as f:
        return json.load(f)


def execute_plan(file_path,new_content):

    execution_id = str(uuid.uuid4())

    create_backup(
        file_path,
        execution_id
    )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        old_content = f.read()

    diff = generate_diff(
        old_content,
        new_content
    )

    os.makedirs(
        DIFF_DIR,
        exist_ok=True
    )

    diff_file = os.path.join(
        DIFF_DIR,
        f"{execution_id}.diff"
    )

    with open(diff_file, "w") as f:
        f.write(diff)

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(new_content)

    execution = {
        "execution_id": execution_id,
        "file_path": file_path,
        "status": "PENDING_REVIEW",
        "diff_file": diff_file
    }

    save_execution(execution)

    return execution


def accept_execution(execution_id):

    execution = load_execution(
        execution_id
    )

    execution["status"] = "ACCEPTED"

    save_execution(execution)

    return {
        "message": "Changes accepted"
    }


def reject_execution(execution_id):

    execution = load_execution(
        execution_id
    )

    file_path = execution["file_path"]

    backup_file = os.path.join(
        BACKUP_DIR,
        execution_id,
        os.path.basename(file_path)
    )

    shutil.copy2(
        backup_file,
        file_path
    )

    execution["status"] = "REJECTED"

    save_execution(execution)

    return {
        "message": "Changes reverted"
    }

