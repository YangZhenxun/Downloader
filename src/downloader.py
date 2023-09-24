import argparse
import os
import requests
import multitasking
import signal
import multiprocessing
import time
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                           TimeRemainingColumn, TransferSpeedColumn)
import PyTaskbar
console = Console()
prog = PyTaskbar.Progress()
prog.init()
signal.signal(signal.SIGINT, multitasking.killall)

def split(num_threads, filesize):
    chunk_size = filesize // num_threads
    parts = []
    for i in range(num_threads):
        start = chunk_size * i
        end = start + chunk_size - 1 if i < num_threads - 1 else filesize - 1
        parts.append((start, end))
    return parts



def main(url, num_threads, auto, retry_nums):
    filepath = "..\\Downloaded files\\"
    filename = os.path.normpath(os.path.basename(parse.urlparse(url).path))
    user_agent = UserAgent().random
    ses = requests.session()
    ses.keep_alive = False
    req = ses.head(url, headers={'User-Agent': user_agent}, \
                  stream=True, timeout=60, verify=False)
    total = int(req.headers.get('content-length', 0))
    if auto:
        num_threads = int(multiprocessing.cpu_count() * 2 + 2)
        print(f"thread nums: {num_threads}")
    f = open(filepath+filename, "wb")
    @retry(tries=retry_nums)
    @multitasking.task
    def start_download(start, end):
        progress.start_task(task_id)
        prog.setState('normal')
        _headers = {'User-Agent': user_agent, 'Range': f'bytes={start}-{end}'}
        resp = ses.get(url, headers=_headers, stream=True)
        chunk_size = 2048
        chunks = []
        for chunk in resp.iter_content(chunk_size=chunk_size):
            chunks.append(chunk)
            progress.update(task_id, advance=len(chunk))
            prog.setProgress(len(chunk))
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        del chunks
    parts = split(num_threads, total)
    threads = []
    with Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        " ",
        DownloadColumn(),
        " ",
        TransferSpeedColumn(),
        " eta ",
        TimeRemainingColumn(),
) as progress:
        task_id = progress.add_task("Download file:", filename=filename, start=False)
        progress.update(task_id, total=total)
        for part in parts:
            start, end = part
            start_download(start, end)
        multitasking.wait_for_tasks()
        f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A downloader.")
    parser.add_argument('-U', '--url', type=str, required=True)
    parser.add_argument('--thread-num', type=int, required=False, default=64)
    parser.add_argument('-A', '--auto', action='store_true', default=False, required=False)
    parser.add_argument('--retry-nums', type=int, required=False, default=3)
    arg = parser.parse_args()
    start = time.perf_counter()
    main(arg.url, arg.thread_num, arg.auto, arg.retry_nums)
    end = time.perf_counter()
    print(end - start)
