import argparse
import os
import warnings

import aiohttp
import asyncio
import time
import multiprocessing
import aiofiles
import re
from aiopath import AsyncPath
from retry import retry
from fake_useragent import UserAgent
from urllib import parse
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                           TimeRemainingColumn, TransferSpeedColumn, TaskID)
console = Console()
policy = asyncio.WindowsSelectorEventLoopPolicy()
asyncio.set_event_loop_policy(policy)


async def total(url: str, session: aiohttp.ClientSession, header: dict) -> list:
    """_summary_

    Args:
        url (str): Url.
        session (aiohttp.ClientSession): A client session from aiohttp.
        header (dict): A link header.

    Returns:
        int: The file's total.
    """
    async with session.get(url, headers=header, timeout=aiohttp.ClientTimeout(total=60)) as req:
        print(req.headers)
        gf = asyncio.create_task(get_filename(req.headers))
        lenf = req.headers.get('content-length')
        if lenf == None or int(lenf) == 0:
            return [None, gf]
        else:
            return [int(lenf), gf]


async def get_filename(header: dict):
    _filename = header.get('Content-Disposition')
    if not _filename:
        return None
    dtaf = re.search("([a-zA-Z]+)(; filename=(.+))?", _filename, re.I | re.M)
    downd_type = dtaf.group(1)
    if downd_type != "attachment":
        warnings.warn("It will download this .html file!Are you sure?")
    downd_file = dtaf.group(3)
    if downd_file:
        return downd_file
    else:
        return None


async def split(filesize: int, num_threads: int) -> list[tuple[int, int]]:
    """Split file size

    Args:
        filesize (int): The file size.
        num_threads (int): The number of threads.

    Returns:
        list[tuple[int, int]]: Chucks.
    """
    chunk_size: int = filesize // num_threads
    parts: list[tuple[int, int]] = []
    for i in range(num_threads):
        _start: int = chunk_size * i
        _end: int = _start + chunk_size - 1 if i < num_threads - 1 else filesize
        parts.append((_start, _end))
    print(parts)
    return parts


async def main(url: str, retry_nums: int, coros: int, semaphores: int) -> None:
    """Main function for running.

    Args:
        url (str): Url.
        retry_nums (int): __des__
        coros (int): __des__
        semaphores(int):__des__
    """
    main_dir: AsyncPath = (await AsyncPath(__file__).resolve()).parents[1]
    download_dir: AsyncPath = await AsyncPath(main_dir / "Downloaded files\\").resolve()
    download_file: AsyncPath = download_dir / os.path.normpath(os.path.basename(parse.urlparse(url).path))
    user_agent: str = UserAgent().random

    @retry(tries=retry_nums)
    async def start_download(_start: int, _end: int, _session: aiohttp.ClientSession, _download_file):
        async with aiofiles.open(file=_download_file, mode="wb+") as f:
            """_summary_
            Args:
                start (int): _description_
                end (int): _description_
                session (aiohttp.ClientSession): _description_
            """
            progress.start_task(task_id)
            await f.seek(_start, 0)
            _headers: dict = {'User-Agent': user_agent, 'Range': f'bytes={_start}-{_end}'}
            timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=100000**10)
            async with _session.get(url, headers=_headers, timeout=timeout) as req:
                async for chunk, _ in req.content.iter_chunks():
                    await f.write(chunk)
                    progress.update(task_id, advance=len(chunk))

    @retry(tries=retry_nums)
    async def chunk_download(_session: aiohttp.ClientSession, _download_file):
        async with aiofiles.open(file=_download_file, mode="wb+") as f:
            _headers: dict = {'User-Agent': user_agent}
            timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=100000 ** 10)
            async with _session.get(url, headers=_headers, timeout=timeout) as req:
                async for chunk, _ in req.content.iter_chunks():
                    await f.write(chunk)
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
        tasks: list = []
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=semaphores)) as session:
            __total = await asyncio.create_task(total(url, session, {'User-Agent': user_agent}))
            _total = __total[0]
            _filename = await __total[1]
            if _filename == None:_filename = download_file
            else: _filename = download_dir / _filename
            if _total == None:
                await asyncio.create_task(chunk_download(session, _filename))
            else:
                progress.update(task_id, total=_total)
                parts = await asyncio.create_task(split(_total, coros))
                print(len(parts))
                for part in parts:
                    __start, __end = part
                    tasks.append(asyncio.create_task(start_download(__start, __end, session, _filename)))
                _done = await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description="A downloader.")
        parser.add_argument('-U', '--url', type=str, required=True)
        parser.add_argument('--retry-nums', type=int, required=False, default=3)
        parser.add_argument('-C', "--concurrent-nums", type=int, required=False,
                            default=multiprocessing.cpu_count()*2+2)
        parser.add_argument('-S', "--semaphores", type=int, required=False, default=3)
        arg = parser.parse_args()
        start = time.perf_counter()
        asyncio.run(main(arg.url, arg.retry_nums, arg.concurrent_nums, arg.semaphores))
        end = time.perf_counter()
        print(end - start)
    except Exception:
        console.print_exception()