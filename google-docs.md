# Development Steps

To upload to Google Docs in development you can follow these steps. We will need to obtain Google API credentials (`GOOGLE_SERVICE_ACCOUNT_CREDENTIALS`) and a Google Docs Folder (`GDOC_GOOGLE_FOLDER_ID`) to upload to. We will use these 2 environment variables to generate DOCX files and then upload them to Google.

## Obtain GOOGLE_SERVICE_ACCOUNT_CREDENTIALS

Sign in to https://console.cloud.google.com 

Click “Select a Project” from the horizontal blue bar at the top of the screen and then select “New Project” from the modal

Choose a name for the project (it has to be unique) like “openstax-pipeline-gdocs-1234” and be sure that “**No Organization**” is selected and select “**Create**”. If you cannot select No Organization try using a non-rice Google account (Rice prevents employees from creating Service Accounts).

Now select the project (for me it was in the Notifications menu). You should see the following:

Next, we need to enable the Google Drive API. Click “**Go to APIs Overview**” (or visit this link and then select the project: https://console.cloud.google.com/apis ):

Click “Enable APIs and Services” and select the Google Drive API:

Enable Google Drive API:

Add a Service Account by opening the hamburger menu at the top-left, select **IAM & Admin**, and then select **Service Accounts**:

Click “**Create Service Account**”:

Enter a name, skip the rest of the input boxes, and click **Done**.

**Note:** Remember this email. You will share a Google Docs folder with it later on.

Select the service account you just created, switch to the **Keys** tab, click **Add Key** and then click **Create New Key**

Choose the JSON format, click **Create**, and then save the file locally. It should be named something like `openstax-pipeline-gdocs-1234-d34db33f.json`

With those steps we now have the GOOGLE_SERVICE_ACCOUNT_CREDENTIALS entry. Note: the JSON in the file should have about 10 fields including type, project_id, private_key_id, private_key, client_id, client_email, auth_uri, …

## Obtain GDOC_GOOGLE_FOLDER_ID

Now we need to create a folder and share the folder with the service account.

In https://drive.google.com create a new Folder (e.g. “Test GDocs Root” ) and share it with the email address of the service account you created earlier (e.g. `test-service-account@openstax-pipeline-gdocs-1234.iam.gserviceaccount.com`)

## Build some DOCX files

Use the [CLI](./cli.sh) to generate DOCX files for a book. For example: (the exact syntax is subject to change):

```sh
./cli.sh ./data/socio all-archive-gdoc col11762 sociology latest
```

## Upload the DOCX files to Google Drive

Run the following to Upload to Google Drive:

```sh
GDOC_GOOGLE_FOLDER_ID='kqj24h9s8fsdfh_98324hkajehr' \
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS="$(cat ~/Downloads/openstax-pipeline-gdocs-1234-d34db33f.json)" \
./cli.sh ./data/socio archive-upload-docx
```

As a bonus, you can run it again to verify the files are updated instead of created (logs will say “Updating” instead of “Creating”)