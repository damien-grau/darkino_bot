from colorama import Fore
import datetime

class DarkinoLog:
    def __init__(self, filename: str = "darkino_log.txt") -> None:
        self.filename = filename
        self.__colors = {
            "RED": Fore.RED,
            "GREEN": Fore.GREEN,
            "RESET": Fore.RESET,
            "YELLOW": Fore.YELLOW
        }
    
    def print_log(self, title: str, value: str, color: str = None, save: bool=False) -> None:
        """_summary_

        Args:
            title (str): log title
            value (str): log description
            color (str, optional): log color Defaults to None.
            save (bool, optional): save log in file. Defaults to False.
        """
        if not color:
            color = self.__colors["RESET"]
        elif self.__colors.get(color.upper()):            
            color = self.__colors[f"{color.upper()}"]

        log_value = f"[{datetime.datetime.now()}] [LOG] {title} : {value}"
        print(color + log_value)
        if save:
            self.__save_log__(log_value=log_value)
    
    def __save_log__(self, log_value: str):
        with open(self.filename, "a") as f:
            f.write(log_value + "\n")

