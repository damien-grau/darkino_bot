import datetime
import requests
from bs4 import BeautifulSoup
from colorama import Fore
import codecs
from dotenv import load_dotenv
import os
from darkinolog import DarkinoLog

darkino_log = DarkinoLog()
load_dotenv()

URL_LAST_2023 = os.getenv("URL_LAST_2023") + os.getenv("GET_REQUEST")


def __get_film_info__(movie, **kwargs):
    """
    Retrieve description of the film, actors, gender, yt trailer
    :movie: dictionnary of the film
    :return: tuple => description, actors, gender, yt trailer link, list of files uploaded
    """
    if "log" in kwargs:
        log = kwargs["log"]
    else:  
        log = True
    soup_temp = BeautifulSoup(__get_page__(movie["redirect_url"], log), "html.parser")

    desc = soup_temp.find("span", string="Synopsis")
    if desc:
        desc = desc.findNextSiblings()[0].getText().strip()
    else:
        desc = "-"
        darkino_log.print_log("Scrapping Error", f"No Synopsis match for \"{movie['title']}\"", "RED", save=True)

    actors_list = soup_temp.find("span", string="Acteurs")
    if actors_list:
        actors_list = actors_list.findNextSiblings()[0].findChildren()
        actors = ", ".join([gender.getText() for gender in actors_list])
    else:
        actors = "-"
        darkino_log.print_log("Scrapping Error", f"No Actors match for \"{movie['title']}\"", "RED", save=True)


    gender_list = soup_temp.find("span", string="Genre")
    if gender_list:
        gender_list = gender_list.findNextSiblings()[0].findChildren()
        genders = ", ".join([gender.getText() for gender in gender_list])
    else:
        genders = "-"
        darkino_log.print_log("Scrapping Error", f"No Gender match for \"{movie['title']}\"", "RED", save=True)

    trailer_link = ""
    embed = soup_temp.find("iframe")
    if embed: 
        embed_link = embed["src"]
        embed_page = str(codecs.decode(__get_page__(embed_link), "unicode-escape"))
        
        NOT_FOUND = -1
        patterns = ["https://www.youtube.com/watch?", "http://www.youtube.com/watch?"]
        start_index = int(embed_page.find(patterns[0]))
        if start_index == NOT_FOUND:
            start_index = int(embed_page.find(patterns[1]))
        if start_index != NOT_FOUND:
            # Select the entire link. The v value can't be greater than 11 characters.
            trailer_link = embed_page[start_index:start_index+43]
        else:
            darkino_log.print_log("Matching Error", "No matching patterns to a Youtube Video URL found", "RED", save=True)
    else:
        darkino_log.print_log("Scrapping Error", f"Trailer Link not found for \"{movie['title']}\"", "RED", save=True)
    
    # Fetching all files uploaded
    tbody = soup_temp.find("div", {"x-show": "tab === '1fichier'"}).findChildren(recursive=False)[0].findChildren(recursive=False)[0].findChildren(recursive=False)[0].findChildren(recursive=False)[1].findChildren(recursive=False)[0].findChildren(recursive=False)[1].findChildren(recursive=False)
    all_film_files = []
    for item in tbody:
        link = item.findChildren(recursive=False)[1].find("a")["href"]
        size = item.findChildren(recursive=False)[3].find("span").text.strip()
        quality = item.findChildren(recursive=False)[4].find("span").text.strip()
        lang = " ".join([span.text.replace("\n", "") for span in item.findChildren(recursive=False)[5].findAll("span", {"class": "badge bg-primary space-x-7"})])

        all_film_files.append([link, size, quality, lang])
        
    """ 
    Triage des doublons par qualité, taille, langue
    
    Pour chaque film dans tous les films:
    Si film est dans dict ET langue du film dans dict pas FR ET langue du film pas dans dict est FR ALORS remplace dans dict
    SINON SI Dans dict  ET taille film < taille film dans dict ALORS remplace dans dict
    SI PAS DANS DICT: ajoute dans dict

    FORMAT (examples):
    lang | film[4]: str = "TrueFrench English"
    """
    films_dict = {}
    fr_lang = ["French", "TrueFrench", "MULTI"]
    for film in all_film_files:
        if (film[2] in films_dict and any(lang not in fr_lang for lang in films_dict[film[2]][3].split(" ")) and any(lang in fr_lang for lang in film[3].split(" "))) or \
            (film[2] in films_dict and float(film[1].split(" ")[0]) < float(films_dict[film[2]][1].split(" ")[0]) or \
                (film[2] not in films_dict)):
            films_dict[film[2]] = film
    sorted_films = list(films_dict.values())
    # Convert sorted_list in string for discord embed
    all_files_string = "\n".join([f"[Télécharger]({item[0]}) - {item[1]} - {item[2]} - {item[3]}" for item in sorted_films])
    darkino_log.print_log("Fetched files", f"{len(sorted_films)} file(s) found for {movie['title']}", "GREEN")
    return desc, actors, genders, trailer_link, all_files_string


def __get_page__(url: str, log: bool = True) -> bool | bytes:
    """
    Get page content
    :param url: url to the website
    :return: the content of the webpage if HTTP code is 200, else return False
    """
    client = requests.Session()
    client.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36'})
    try:
        response = client.get(url)
    except requests.exceptions.ConnectionError:
        darkino_log.print_log("ConnectionError", f"The server refused the connexion. Url : {url}", "RED", save=True)
        return False
    except Exception as e:
        darkino_log.print_log("UncommonError", f"An unusual error has occurred : {e}", "RED", save=True)
        return False
    finally:
        client.close()

    if not response.ok:
        if log:
            darkino_log.print_log("HTTP request", f"{response.status_code} for {url}", "RED", save=True)
        return False
    if log:
        darkino_log.print_log("HTTP request", f"{response.status_code} for {url}", "GREEN")
    return response.content


def get_all_latest() -> list[dict] | bool:
    """
    This function return 32 latest movies of 2023.
    Can return False if the website is not accessible
    :return: a list of dictionaries or boolean
    """
    page_source = __get_page__(URL_LAST_2023)

    if not page_source:
        return False
    soup = BeautifulSoup(page_source, "html.parser")
    try:
        all_last_films = soup.find_all("div", {"class": "videos"})[0].findChildren()[0]
    except IndexError as e:
        darkino_log("Script Error - IndexError", f"An error occured when fetching all films : {e}", "RED", save=True)
        return False

    # Sort all the movies in a list of dictionnary
    sorted_all_movies = []
    for film in all_last_films:
        if len(film) <= 1:
            continue
        iterator = film.findChildren()[0].findChildren()[0]
        sorted_all_movies.append({
            "title": iterator.findChildren()[0].findChildren()[0]["alt"],  # Title of the film
            "img_url": iterator.findChildren()[0].findChildren()[0]["src"],  # Link of the film poster
            "year_prod": iterator.findChildren()[0].findNextSiblings()[0].contents[0].text,  # Year Production
            "date_post": iterator.findChildren()[0].findNextSiblings()[1].contents[0].text,  # Date Post Darkino
            "redirect_url": iterator.findChildren()[0]["href"]
        })

    return sorted_all_movies
