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


def enters_the_window(canvas, row, column, frame):
    window_height, window_width = canvas.getmaxyx()
    frame_height, frame_width = get_frame_size(frame)

    if row + frame_height < window_height and \
            column + frame_width < window_width:
        return True

    return False


def draw(canvas):
    with open(
        os.path.join("animations", "rocket", "rocket_frame_1.txt"), "r"
    ) as my_file:
        rocket_frame_1 = my_file.read()

    with open(
        os.path.join("animations", "rocket", "rocket_frame_2.txt"), "r"
    ) as my_file:
        rocket_frame_2 = my_file.read()

    garbage_frames_path = os.listdir(os.path.join("animations", "garbage"))

    garbage_frames = []

    for garbage_frame_path in garbage_frames_path:
        with open(
            os.path.join("animations", "garbage", f"{garbage_frame_path}"), "r"
        ) as garbage_file:
            garbage_frames.append(garbage_file.read())

    pading = 2
    iter_count = 1
    stars_count = 50

    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)
    window_height, window_width = canvas.getmaxyx()

    year_box_height = 2
    year_box_width = 60
    year_box_row = round(window_height * 0.8)
    year_box_column = window_width // 2

    year_box = canvas.derwin(
        year_box_height,
        year_box_width,
        year_box_row,
        year_box_column
    )
    coroutines = []
    garbage_coroutines = []

    blink_coroutines = [
        blink(
            canvas=canvas,
            row=randint(1, window_height - pading),
            column=randint(1, window_width - pading),
            symbol=choice('★⚝✷*.○+●°•☆:☼❃')
        ) for num in range(stars_count)]

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
            start_row=window_height / 3,
            start_column=window_width / 3,
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
                        column=randint(1, window_width),
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
    row = 1
    column = 1

    while True:
        if year in PHRASES:
            year_box.addstr(row, column, "Year: " + str(year) + " " + PHRASES[year])
        else:
            year_box.addstr(row, column, "Year: " + str(year))
        await asyncio.sleep(0)


async def show_win(canvas):
    with open(os.path.join("animations", "win.txt"), "r") as win_file:
        screensaver = win_file.read()

    window_height, window_width = canvas.getmaxyx()
    screensaver_window_height, screensaver_window_width = get_frame_size(
        screensaver
    )
    start_column = (window_width - screensaver_window_width) // 2
    start_row = (window_height - screensaver_window_height) // 2

    while True:
        if enters_the_window(
            canvas=canvas,
            row=start_row,
            column=start_column,
            frame=screensaver
        ):

            draw_frame(
                canvas=canvas,
                start_row=start_row,
                start_column=start_column,
                text=screensaver,
            )

        await asyncio.sleep(0)


async def show_gameover(canvas):
    with open(
        os.path.join("animations", "game_over.txt"), "r"
    ) as game_over_file:
        screensaver = game_over_file.read()

    window_height, window_width = canvas.getmaxyx()
    screensaver_window_height, screensaver_window_width = get_frame_size(
        screensaver
    )
    start_column = (window_width - screensaver_window_width) // 2
    start_row = (window_height - screensaver_window_height) // 2

    while True:
        if enters_the_window(
            canvas=canvas,
            row=start_row,
            column=start_column,
            frame=screensaver
        ):

            draw_frame(
                canvas=canvas,
                start_row=start_row,
                start_column=start_column,
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

    window_height, window_width = canvas.getmaxyx()
    max_row, max_column = window_height - 1, window_width - 1

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
    window_height, window_width, = canvas.getmaxyx()
    height_pading, width_pading = 1, 1

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

        if (start_row + row_speed + frame_row) >= window_height \
                and row_speed > 0:
            start_row = window_height - frame_row - height_pading

        elif (start_row + row_speed) <= 1 and row_speed < 0:
            start_row = 1

        else:
            start_row += row_speed

        if (start_column + column_speed + frame_column) >= window_width \
                and column_speed > 0:
            start_column = window_width - frame_column - width_pading

        elif (start_column + column_speed) <= 1 and column_speed < 0:
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
    window_height, window_width = canvas.getmaxyx()
    pading = 1

    column = max(column, 0)
    rows_size, columns_size = get_frame_size(garbage_frame)
    column = min(column, window_width - columns_size - pading)
    row = 0

    obstacle = Obstacle(row, column, rows_size, columns_size)

    obstacles_coroutines.append(obstacle)

    while row < window_height:
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
