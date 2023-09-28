import requests
import multitasking
import multiprocessing
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                        TimeRemainingColumn, TransferSpeedColumn, TaskID)

def main_download(url: str, parts: list[tuple[int, int]], retry_nums: int, \
                name: str, total: int, num_threads: int, taskid: TaskID, \
                progress: Progress, ses: requests.Session) -> None:
    """_summary_

    Args:
        url (str): _description_
        parts (list[tuple[int, int]]): _description_
        retry_nums (int): _description_
        total (int): _description_
        num_threads (int): _description_
        taskid (TaskID): _description_
        ses (requests.Session): _description_
    """
    @retry(tries=retry_nums)
    @multitasking.task
    def start_download(start: int, end: int) -> None:
        """_summary_

        Args:
            start (int): _description_
            end (int): _description_
        """
        with open(name, "wb") as f:
            f.seek(start)
            _headers:dict[str, str] = {'User-Agent': user_agent, 'Range': f'bytes={start}-{end}', 'Content-Type': 'application/octet-stream'}
            resp = ses.get(url, headers=_headers, stream=True)
            chunk_size = 2048
            for chunk in resp.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                progress.update(task_id, advance=total)
    task_id = progress.add_task("Download file:", filename=filename, start=False)
    progress.update(task_id, total=total)
    for part in parts:
        (start, end) = part
        start_download(start, end)
    multitasking.wait_for_tasks()
