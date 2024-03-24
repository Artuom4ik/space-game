import os
import time
import curses
import asyncio
from random import randint, choice
from itertools import cycle

from curses_tools import draw_frame, read_controls, get_frame_size


TIC_TIMEOUT = 0.1


def draw(canvas):
    with open("animations/rocket/rocket_frame_1.txt", "r") as my_file:
        rocket_frame_1 = my_file.read()

    with open("animations/rocket/rocket_frame_2.txt", "r") as my_file:
        rocket_frame_2 = my_file.read()

    garbage_frames_path = os.listdir("animations/garbage")

    garbage_frames = []

    for garbage_frame_path in garbage_frames_path:
        with open(f'animations/garbage/{garbage_frame_path}', "r") as garbage_file:
            garbage_frames.append(garbage_file.read())


    pading = 2
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    rocket = animate_spaceship(
        canvas,
        start_row=canvas.getmaxyx()[0] / 3,
        start_column=canvas.getmaxyx()[1] / 3,
        frames=[
            rocket_frame_1, rocket_frame_1,
            rocket_frame_2, rocket_frame_2
        ])
    coroutines = [
        blink(
            canvas,
            randint(1, canvas.getmaxyx()[0] - pading),
            randint(1, canvas.getmaxyx()[1] - pading),
            choice('★⚝✷*.○+●°•☆:☼❃')
        ) for num in range(50)]

    while True:
        for num in range(len(coroutines)):
            coroutines[randint(0, len(coroutines)) - 1].send(None)

        rocket.send(None)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)

    time.sleep(1)


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for i in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for i in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(3):
            await asyncio.sleep(0)


async def animate_spaceship(canvas, start_row, start_column, frames):
    frame_row, frame_column = get_frame_size(frames[0])
    for frame in cycle(frames):
        row, column, space = read_controls(canvas)
        row *= 3
        column *= 3

        if row > 0:
            if (start_row + row + frame_row) >= canvas.getmaxyx()[0]:
                start_row = canvas.getmaxyx()[0] - frame_row - 1

            else:
                start_row += row

        if row < 0:
            if (start_row + row) <= 1:
                start_row = 1

            else:
                start_row += row

        if column > 0:
            if (start_column + column + frame_column) >= canvas.getmaxyx()[1]:
                start_column = canvas.getmaxyx()[1] - frame_column - 1

            else:
                start_column += column

        if column < 0:
            if (start_column + column) <= 1:
                start_column = 1

            else:
                start_column += column

        draw_frame(canvas, start_row, start_column, frame)
        await asyncio.sleep(0)

        draw_frame(canvas, start_row, start_column, frame, negative=True)
        draw_frame(canvas, start_row, start_column, frame)
        await asyncio.sleep(0)

        draw_frame(canvas, start_row, start_column, frame, negative=True)


async def fire(canvas,
               start_row,
               start_column,
               rows_speed=-0.3,
               columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
