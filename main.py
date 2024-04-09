import os
import time
import curses
import asyncio
from random import randint, choice
from itertools import cycle

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle
from explosion import explode
from game_scenario import PHRASES, get_garbage_delay_tics


TIC_TIMEOUT = 0.1
obstacles_coroutines = []
collision_obstacles = []
year = 1956
phrase = ""


def draw(canvas):
    with open("animations/rocket/rocket_frame_1.txt", "r") as my_file:
        rocket_frame_1 = my_file.read()

    with open("animations/rocket/rocket_frame_2.txt", "r") as my_file:
        rocket_frame_2 = my_file.read()

    garbage_frames_path = os.listdir("animations/garbage")

    garbage_frames = []

    for garbage_frame_path in garbage_frames_path:
        with open(
            f'animations/garbage/{garbage_frame_path}', "r"
        ) as garbage_file:
            garbage_frames.append(garbage_file.read())

    pading = 2
    iter_count = 1

    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)
    window_width, window_height = canvas.getmaxyx()
    year_box = canvas.derwin(
        2,
        60,
        window_height // 5,
        window_width * 2
    )
    coroutines = []
    garbage_coroutines = []

    blink_coroutines = [
        blink(
            canvas,
            randint(1, window_width - pading),
            randint(1, window_height - pading),
            choice('★⚝✷*.○+●°•☆:☼❃')
        ) for num in range(50)]

    coroutines += blink_coroutines

    coroutines.append(
        fill_orbit_with_garbage(
            canvas=canvas,
            garbage_coroutines=garbage_coroutines,
            garbage_frames=garbage_frames,
        )
    )

    coroutines.append(
        animate_spaceship(
            canvas,
            start_row=window_width / 3,
            start_column=window_height / 3,
            frames=[
                rocket_frame_1, rocket_frame_1,
                rocket_frame_2, rocket_frame_2
            ],
            coroutines=coroutines,
        )
    )

    coroutines.append(update_year())
    coroutines.append(show_year(year_box=year_box))

    while True:
        if get_garbage_delay_tics(year):
            if not iter_count % (2 * get_garbage_delay_tics(year)):
                garbage_coroutines.append(
                    fly_garbage(
                        canvas=canvas,
                        column=randint(1, window_height),
                        garbage_frame=choice(garbage_frames),
                        speed=1.0,
                    )
                )

        for coroutine in coroutines:
            try:
                coroutine.send(None)

            except StopIteration:
                coroutine.close()

            except RuntimeError:
                coroutines.remove(coroutine)

            finally:
                canvas.border()

        iter_count += 1
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)

    time.sleep(1)


async def update_year():
    global year

    while True:
        year += 1
        await sleep(15)


async def show_year(year_box):
    global phrase

    while True:
        if year in PHRASES:
            phrase = PHRASES[year]
            year_box.addstr(1, 1, "Year: " + str(year) + " " + phrase)
        else:
            year_box.addstr(1, 1, "Year: " + str(year) + " " + phrase)
        await asyncio.sleep(0)


async def show_win(canvas):
    with open("animations/win.txt", "r") as win_file:
        screensaver = win_file.read()

    window_width, window_height = canvas.getmaxyx()
    screensaver_window_width, screensaver_window_height = get_frame_size(
        screensaver
    )
    while True:
        draw_frame(
            canvas=canvas,
            start_row=(window_width - screensaver_window_width) // 2,
            start_column=(window_height - screensaver_window_height) // 2,
            text=screensaver,
        )

        await asyncio.sleep(0)


async def show_gameover(canvas):
    with open("animations/game_over.txt", "r") as game_over_file:
        screensaver = game_over_file.read()

    window_width, window_height = canvas.getmaxyx()
    screensaver_window_width, screensaver_window_height = get_frame_size(
        screensaver
    )
    while True:
        draw_frame(
            canvas=canvas,
            start_row=(window_width - screensaver_window_width) // 2,
            start_column=(window_height - screensaver_window_height) // 2,
            text=screensaver,
        )

        await asyncio.sleep(0)


async def sleep(tics=1):
    for i in range(tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


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

    window_width, window_height = canvas.getmaxyx()
    max_row, max_column = window_width - 1, window_height - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')

        for obstacle in obstacles_coroutines:
            if obstacle.has_collision(row, column):
                collision_obstacles.append(obstacle)
                return

        row += rows_speed
        column += columns_speed


async def animate_spaceship(
        canvas,
        start_row,
        start_column,
        frames,
        coroutines):

    frame_row, frame_column = get_frame_size(frames[0])
    row_speed = column_speed = 0
    window_width, window_height, = canvas.getmaxyx()

    for frame in cycle(frames):
        if year >= 2077:
            await show_win(canvas)
            return

        row, column, space = read_controls(canvas)
        row_speed, column_speed = update_speed(
            row_speed,
            column_speed,
            row,
            column
        )

        for obstacle in obstacles_coroutines:
            if obstacle.has_collision(start_row, start_column):
                await show_gameover(canvas)
                return

        if space and year >= 2020:
            coroutines.append(
                fire(
                    canvas=canvas,
                    start_row=start_row,
                    start_column=start_column + 2,
                    rows_speed=-1,
                )
            )

        if row_speed > 0:
            if (start_row + row_speed + frame_row) >= window_width:
                start_row = window_width - frame_row

            else:
                start_row += row_speed

        if row_speed < 0:
            if (start_row + row_speed) <= 1:
                start_row = 1

            else:
                start_row += row_speed

        if column_speed > 0:
            if (start_column + column_speed + frame_column) >= window_height:
                start_column = window_height - frame_column

            else:
                start_column += column_speed

        if column_speed < 0:
            if (start_column + column_speed) <= 1:
                start_column = 1

            else:
                start_column += column_speed

        draw_frame(canvas, start_row, start_column, frame)
        await asyncio.sleep(0)

        draw_frame(canvas, start_row, start_column, frame, negative=True)
        draw_frame(canvas, start_row, start_column, frame)
        await asyncio.sleep(0)

        draw_frame(canvas, start_row, start_column, frame, negative=True)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    window_width, window_height = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, window_height - 1)
    rows_size, columns_size = get_frame_size(garbage_frame)
    row = 0

    obstacle = Obstacle(row, column, rows_size, columns_size)

    obstacles_coroutines.append(obstacle)

    while row < window_width:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed

        if obstacle in collision_obstacles:
            obstacles_coroutines.remove(obstacle)
            await explode(canvas, obstacle.row, obstacle.column)
            return

        else:
            obstacle.row += speed


async def fill_orbit_with_garbage(canvas, garbage_coroutines, garbage_frames):
    while True:
        for garbage_coroutine in garbage_coroutines:
            try:
                garbage_coroutine.send(None)

            except StopIteration:
                garbage_coroutine.close()

            except RuntimeError:
                garbage_coroutines.remove(garbage_coroutine)

        await asyncio.sleep(0)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
