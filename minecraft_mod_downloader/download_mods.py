import logging
from json import dump as json_dump, load as json_load, loads as json_load_from_string
from os import listdir, path as os_path, remove as os_remove
from pathlib import Path
from re import findall as re_findall, search as re_search
from urllib.parse import unquote as url_unquote

from requests import get as requests_get

logging.getLogger().setLevel(logging.INFO)

CONFIG_FILE = Path("C:/Users/mj_no/Documents/Personal/Games/Minecraft/Mods.json")
MODS_FOLDER = Path("C:/Users/mj_no/AppData/Roaming/.minecraft/mods/")
# noinspection SpellCheckingInspection
CURSEFORGE_API_KEY = "$2a$10$MOys6gf/.H.hUiEudS3pVu1Eao/iJ4mR8AAbSxegegLyTPtTJVOEu"
FORCE_DOWNLOAD = False


def get_latest_major_minecraft_version(latest_minecraft_version):
    temp = latest_minecraft_version.split(".")
    return temp[0] + "." + temp[1]


def get_latest_minecraft_version():
    dir_path = r"C:\Users\mj_no\AppData\Roaming\.minecraft\versions"

    class Version:
        def __init__(self, name: str):
            self.version_num: str | None = None
            self.name = name

        def __repr__(self):
            return f"'{self.name}'"

    directories = [entry for entry in listdir(dir_path) if os_path.isdir(os_path.join(dir_path, entry))]
    fabric_versions = [directory for directory in directories if re_findall(r"^.*fabric.*$", directory)]
    matches = [re_findall(r"\d+\.\d+\.?\d*", string) for string in fabric_versions]
    temp: list[Version] = []
    for fabric_version in fabric_versions:
        temp.append(Version(fabric_version))
    fabric_versions = temp

    for index in range(0, len(matches)):
        version = matches[index]
        this_version = version[0]
        for index2 in range(1, len(version)):
            this_version += "." + version[index2]
        fabric_versions[index].version_num = this_version

    matches = sorted(fabric_versions, key=lambda x: tuple(map(int, x.version_num.split("."))))

    return matches[-1].name


def main():
    latest_minecraft_version = re_search(r"1\.\d+\.\d+", get_latest_minecraft_version()).group()
    logging.info(f"Checking mods for Minecraft {latest_minecraft_version}")
    FALLBACK_VERSIONS = [latest_minecraft_version] + [f"{get_latest_major_minecraft_version(latest_minecraft_version)}.{num}" for num in range(int(latest_minecraft_version.rsplit(".", maxsplit=1)[-1]) - 1, 1, -1)] + [get_latest_major_minecraft_version(latest_minecraft_version)]

    with open(CONFIG_FILE) as json_file:
        data: dict = json_load(json_file)
    modlist = list(data.values())[-1]

    for mod in modlist["Fabric"] + modlist["Quilt"]:
        if "Disabled" not in mod:
            logging.debug(f"""{mod["Name"]} - Begin checking""")
            if mod["Download"] == "Modrinth":
                logging.debug(f"""{mod["Name"]} - Getting latest Modrinth online version""")
                for version in FALLBACK_VERSIONS:
                    logging.info(f"""{mod["Name"]} - Testing to see if an online version exists for {version}""")
                    latest_mod_versions_list = sorted(json_load_from_string(requests_get(f"""https://api.modrinth.com/v2/project/{mod["Mod ID"]}/version?loaders=[\"quilt\",\"fabric\"]&game_versions=[\"{version}\"]""").text), key=lambda x: x["version_number"], reverse=True)

                    if latest_mod_versions_list:
                        logging.info(f"""{mod["Name"]} - Online mod version exists for Minecraft {version}""")
                        break
                    else:
                        logging.warning(f"""{mod["Name"]} - No online mod version exists for Minecraft {version}""")
                else:
                    logging.critical(f"""{mod["Name"]} ({mod["Download"]}) - No compatible mod version can be found online""")
                    logging.critical("Press Enter to continue...")
                    input()
                    continue

                latest_mod_version = latest_mod_versions_list[0]

                if mod.get("Version ID") != latest_mod_version["id"] or FORCE_DOWNLOAD:
                    logging.info(f"""{mod["Name"]} - Update, compared to local mod file, found!""")
                    try:
                        logging.info(f"""{mod["Name"]} - Attempting to remove old version""")
                        os_remove(MODS_FOLDER / mod["File Name"])
                    except FileNotFoundError:
                        logging.info(f"""{mod["Name"]} - No old version found""")
                    except KeyError:
                        logging.warning("No filename provided for this mod in the config file")

                    mod["Version ID"] = str(latest_mod_version["id"])

                    url = latest_mod_version["files"][0]["url"]

                    logging.info(f"""{mod["Name"]} - Downloading new version""")
                    open(MODS_FOLDER / url_unquote(url.split("/")[-1]), "wb").write(requests_get(url).content)

                    logging.debug(f"""{mod["Name"]} - Updating config file""")
                    mod["File Name"] = url_unquote(url.split("/")[-1])

                else:
                    logging.info(f"""{mod["Name"]} - Local mod file is up to date""")

            elif mod["Download"] == "Curseforge":
                logging.debug(f"""{mod["Name"]} - Getting latest Curseforge online version""")

                project: dict = json_load_from_string(requests_get(
                    f"""https://api.curseforge.com/v1/mods/{mod["Mod ID"]}/""",
                    headers={"Accept": "application/json", "x-api-key": CURSEFORGE_API_KEY}
                ).text)["data"]

                for version in FALLBACK_VERSIONS:
                    logging.info(f"""{mod["Name"]} - Testing to see if an online version exists for {version}""")
                    leave = False
                    for latest_mod_version in project["latestFilesIndexes"]:
                        if latest_mod_version["gameVersion"] == version:
                            logging.info(f"""{mod["Name"]} - Online mod version exists for Minecraft {version}""")
                            leave = True
                            break
                    else:
                        logging.warning(f"""{mod["Name"]} - No online mod version exists for Minecraft {version}""")
                    if leave:
                        break
                else:
                    logging.critical(f"""{mod["Name"]} ({mod["Download"]}) - No compatible mod version can be found online""")
                    logging.critical("Press Enter to continue...")
                    input()
                    continue

                # noinspection PyUnboundLocalVariable
                if mod.get("Version ID") != str(latest_mod_version["fileId"]) or FORCE_DOWNLOAD:
                    logging.info(f"""{mod["Name"]} - Update, compared to local mod file, found!""")
                    try:
                        logging.info(f"""{mod["Name"]} - Attempting to remove old version""")
                        os_remove(MODS_FOLDER / mod["File Name"])
                    except FileNotFoundError:
                        logging.warning(f"""{mod["Name"]} - No old version found""")
                    except KeyError:
                        logging.warning("No filename provided for this mod in the config file")

                    mod["Version ID"] = str(latest_mod_version["fileId"])

                    logging.info(f"""{mod["Name"]} - Getting download URL""")

                    url = json_load_from_string(requests_get(
                        f"""https://api.curseforge.com/v1/mods/{mod["Mod ID"]}/files/{latest_mod_version["fileId"]}/download-url""",
                        headers={"Accept": "application/json", "x-api-key": CURSEFORGE_API_KEY}
                    ).text)["data"]

                    logging.info(f"""{mod["Name"]} - Downloading new version""")
                    open(MODS_FOLDER / latest_mod_version["filename"], "wb").write(requests_get(
                        url,
                        headers={"x-api-key": CURSEFORGE_API_KEY}
                    ).content)

                    logging.debug(f"""{mod["Name"]} - Updating config file""")
                    mod["File Name"] = latest_mod_version["filename"]

                else:
                    logging.info(f"""{mod["Name"]} - Local mod file is up to date""")

            else:
                logging.info(f"""{mod["Name"]} - Current mod version: {mod["Version ID"]}""")
                logging.error(f"""Please download {mod["Name"]} at {mod["Download"]}""")
                logging.error("Press Enter to continue...")
                input()

    with open(CONFIG_FILE, "w") as json_file:
        json_dump(data, json_file)


if __name__ == "__main__":
    main()
