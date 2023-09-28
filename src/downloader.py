import argparse
import os
import aiohttp
import asyncio
import time
import multiprocessing
from aiohttp import web
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                        TimeRemainingColumn, TransferSpeedColumn, TaskID)
console = Console()
policy = asyncio.WindowsSelectorEventLoopPolicy()
asyncio.set_event_loop_policy(policy)
semaphore = asyncio.Semaphore(2048)


async def total(url: str, session: aiohttp.ClientSession, header: dict) -> int:
    """_summary_

    Args:
        url (str): _description_
        session (aiohttp.ClientSession): _description_
        header (dict): _description_

    Returns:
        int: _description_
    """
    async with session.head(url, headers=header, timeout=aiohttp.ClientTimeout(total=60)) as req:
        print(req.headers)
        return int(req.headers.get('content-length'))

async def split(filesize: int, num_threads: int) -> list[tuple[int, int]]:
    """Split file size

    Args:
        filesize (int): The file size.
        num_threads (int): The number of threads.

    Returns:
        list[tuple[int, int]]: Chucks.
    """
    chunk_size: int = filesize // num_threads
    parts: dict[tuple[int, int]] = []
    for i in range(num_threads):
        start: int = chunk_size * i
        end: int = start + chunk_size - 1 if i < num_threads - 1 else filesize - 1
        parts.append((start, end))
    return parts

async def main(url: str, retry_nums: int, coros: int) -> None:
    """_summary_

    Args:
        url (str): _description_
        retry_nums (int): _description_
    """
    main_dir: str = os.path.split(os.path.abspath(__file__))[0]
    download_dir: str = os.path.join(os.path.dirname(main_dir), "Downloaded files\\")
    download_file: str = os.path.join(download_dir, os.path.normpath(os.path.basename(parse.urlparse(url).path)))
    user_agent: str = UserAgent().random
    f = open(download_file, "wb")
    @retry(tries=retry_nums)
    async def start_download(start: int, end: int, session: aiohttp.ClientSession) -> None:
        """_summary_

        Args:
            start (int): _description_
            end (int): _description_
            session (aiohttp.ClientSession): _description_
        """
        progress.start_task(task_id)
        f.seek(start)
        _headers: dict[str, str] = {'User-Agent': user_agent, 'Range': f'{start}-{end}', 'Content-Type': 'application/octet-stream', "Accept-Encoding": "gzip, compress, deflate, br"}
        Timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=100000**10)
        async with semaphore:
            async with session.get(url, headers=_headers, timeout=Timeout) as req:
                assert req.status == 200
                async for chunk in req.content.iter_chunked(1024):
                        f.write(chunk)
                        progress.update(task_id, advance=len(chunk))
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
        task_id: TaskID = progress.add_task("Download file:", filename=os.path.split(download_file)[1], start=False)
        tasks: dict = []
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            _total = await asyncio.create_task(total(url, session, {'User-Agent': user_agent, "Accept-Encoding": "gzip, compress, deflate, br"}))
            progress.update(task_id, total=_total)
            parts = await asyncio.create_task(split(_total, coros))
            print(len(parts))
            for part in parts:
                start, end = part
                tasks.append(start_download(start, end, session))
            tasks_a = await asyncio.gather(*tasks)
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A downloader.")
    parser.add_argument('-U', '--url', type=str, required=True)
    parser.add_argument('--retry-nums', type=int, required=False, default=3)
    parser.add_argument('-C', "--concurrent",type=int, required=False, default=multiprocessing.cpu_count()*2+2)
    arg = parser.parse_args()
    start = time.perf_counter()
    asyncio.run(main(arg.url, arg.retry_nums, arg.concurrent))
    end = time.perf_counter()
    print(end - start)
