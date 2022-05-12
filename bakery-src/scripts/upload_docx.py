import sys
from pathlib import Path

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def find_or_create_folder_by_name(drive_service, parent_google_folder_id,
                                  folder_name):
    """Attempt to find existing folder with provided parent or create one if
    not found. Return folder ID of found or created folder.
    """
    # Query for folder to see if it already exists
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and "
          f"'{parent_google_folder_id}' in parents and "
          f"name='{folder_name}'",
        fields='files(id)'
    ).execute()

    items = results.get("files", [])

    if len(items) > 1:
        raise Exception(f"Multiple folders with name '{folder_name}' found.")

    if items:
        return items[0]["id"]

    # Create subfolder under parent since it doesn't already exist
    print(f"Creating folder '{folder_name}' in {parent_google_folder_id}")
    new_folder = drive_service.files().create(
        body={
            "name": folder_name,
            "parents": [parent_google_folder_id],
            "mimeType": "application/vnd.google-apps.folder"
        },
        supportsAllDrives=True,
        fields='id'
    ).execute()
    return new_folder.get('id')


def get_gdocs_in_folder(drive_service, folder_id):
    """Get list of all existing gdoc names and IDs from a folder"""
    page_token = None
    files = []

    # Page results until complete
    while True:
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document' and "
              f"'{folder_id}' in parents ",
            fields='nextPageToken, files(id, name)',
            pageToken=page_token
        ).execute()
        files += results.get('files', [])
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break
    return files


def upsert_docx_to_folder(drive_service, docx_files, book_folder_id):
    """Upsert docx files to google Drive folder"""

    gdocs = get_gdocs_in_folder(drive_service, book_folder_id)
    gdocs_by_name = {doc["name"]: doc["id"] for doc in gdocs}
    upserted_docs = []

    for docx_file in docx_files:
        existing_gdoc_id = gdocs_by_name.get(docx_file.stem)

        # Specify google doc mimeType to trigger conversion from .docx as
        # part of upload processing
        file_metadata = {
            "name": docx_file.stem,
            "mimeType": "application/vnd.google-apps.document"
        }
        media = MediaFileUpload(
            docx_file,
            mimetype="application/vnd.openxmlformats-officedocument."
                     "wordprocessingml.document"
        )
        if existing_gdoc_id:
            # NOTE: For now processing these as upserts which will result in
            # google doc versions, but if we decide later to not allow updates
            # this can throw an error / skip over instead
            drive_service.files().update(
                fileId=existing_gdoc_id,
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            upserted_docs.append(
                {"id": existing_gdoc_id, "name": file_metadata["name"]}
            )
            print(f"Updated {docx_file.name} with file ID {existing_gdoc_id}")
        else:
            file_metadata["parents"] = [book_folder_id]
            upload_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields='id'
            ).execute()
            upserted_docs.append(
                {"id": upload_file["id"], "name": file_metadata["name"]}
            )
            print(f"Created {docx_file.name} as file ID "
                  f"{upload_file['id']}")

    return upserted_docs


def main():  # pragma: no cover
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    book_title = sys.argv[2]
    parent_google_folder_id = sys.argv[3]
    credentials_file_path = Path(sys.argv[4]).resolve(strict=True)

    creds, _ = google.auth.load_credentials_from_file(
        credentials_file_path
    )

    drive_service = build("drive", "v3", credentials=creds)

    book_folder_id = find_or_create_folder_by_name(
        drive_service,
        parent_google_folder_id,
        book_title
    )

    docx_files = in_dir.glob("*.docx")
    upsert_docx_to_folder(
        drive_service,
        docx_files,
        book_folder_id
    )


if __name__ == "__main__":  # pragma: no cover
    main()
