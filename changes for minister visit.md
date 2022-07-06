### Minister visit to UvA July 13th

- Edit `cltl-leolani-app/py-app/config/default.config` and change
    * the `server_image_url` and `server_audio_url` fields under `[cltl.backend]`
    * the `remote_url` field under `[cltl.backend.text_output]`
    * the `greeting` field under `[cltl.leolani.intentions.init]`
    *
- Edit `cltl-leolani-app/py-app/app-leo` and change the `bdi_service` function under the `LeolaniContainer` class to
  skip the GTKY intention
