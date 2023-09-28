from urllib import parse
import fake_useragent
import requests
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                        TimeRemainingColumn, TransferSpeedColumn, TaskID)

console = Console()


def main_download(url: str, name: str, ses: requests.Session, taskid: TaskID, progress: Progress) -> None:
    """_summary_

    Args:
        url (str): _description_
    """
    ses.keep_alive = False
    req = ses.get(url, headers={'User-Agent': user_agent.random}, \
                stream=True, timeout=60, verify=False)
    with open(filepath + filename, "wb") as file:
        progress.start_task(task_id)
        for chunk in req.iter_content(1024):
            size = file.write(chunk)
            progress.update(task_id, advance=size)
