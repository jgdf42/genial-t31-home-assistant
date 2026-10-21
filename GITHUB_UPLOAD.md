# Uploading this integration to GitHub

These steps publish the project as a new public GitHub repository without
including any local Home Assistant configuration, Bluetooth captures, device
addresses, credentials, or account information.

## 1. Choose the repository location

The suggested repository name is:

```text
genial-t31-home-assistant
```

On GitHub, select **New repository**, choose **Public**, and do not initialize
it with a README, `.gitignore`, or license because those files already exist in
this project.

## 2. Update the documentation URL

Before publishing, confirm that
`custom_components/genial_t31/manifest.json` points to the intended repository:

```json
"documentation": "https://github.com/jgdf42/genial-t31-home-assistant"
```

Do not add a code owner unless that GitHub user has agreed to maintain the
integration.

## 3. Review the files

From Terminal:

```bash
cd path/to/genial-t31-ha
find . -type f -not -path './.git/*' -not -path '*/__pycache__/*' | sort
python3 -m unittest discover -s tests -v
```

Verify that the listing contains source code and documentation only. In
particular, do not add Home Assistant backups, `.storage`, logs, packet
captures, APK files, passwords, tokens, or MAC addresses.

The repository also contains reusable automation blueprints and a built-in
dashboard-card example. They are documentation assets and do not contain entity
IDs from any particular Home Assistant installation.

## 4. Create the local Git repository

```bash
cd path/to/genial-t31-ha
git init
git branch -M main
git add .
git status
git commit -m "Initial Genial T31 Home Assistant integration"
git remote add origin https://github.com/jgdf42/genial-t31-home-assistant.git
git push -u origin main
```

GitHub may open a browser or ask you to authenticate. Use a GitHub personal
access token instead of an account password if the command-line prompt asks
for credentials.

## 5. Create the first release

On the GitHub repository page:

1. Select **Releases** and then **Draft a new release**.
2. Create the tag `v1.0.0`.
3. Use `Genial T31 Thermometer 1.0.0` as the release title.
4. Briefly list automatic discovery, local BLE operation, temperature,
   battery, diagnostics, and Bluetooth proxy support.
5. Publish the release.

The version in `manifest.json` must match future release tags without the
leading `v`.

## 6. Install it through HACS for testing

1. In Home Assistant, open **HACS → Integrations**.
2. Open the three-dot menu and select **Custom repositories**.
3. Paste the GitHub repository URL.
4. Select the **Integration** category and add it.
5. Install **Genial T31 Thermometer** and restart Home Assistant.

After testing, future updates can be published by changing the manifest
version, committing the changes, creating a matching Git tag, and publishing a
new GitHub release.

## 7. Test the blueprint links

Open each file under `blueprints/automation/genial_t31` on GitHub, copy its page
URL, and import it through **Settings → Automations & scenes → Blueprints →
Import blueprint**. The relative links in the README will automatically resolve
to the correct repository once it is hosted on GitHub.

