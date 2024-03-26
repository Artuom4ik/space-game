import os
import time
import curses
import asyncio
from random import randint, choice
from itertools import cycle

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle, show_obstacles
from explosion import explode


TIC_TIMEOUT = 0.1
OBSTACLES = []
collision_obstacles = []


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
    iter_count = 0
    fire_coroutines = []
    rocket = animate_spaceship(
        canvas,
        start_row=canvas.getmaxyx()[0] / 3,
        start_column=canvas.getmaxyx()[1] / 3,
        frames=[
            rocket_frame_1, rocket_frame_1,
            rocket_frame_2, rocket_frame_2
        ],
        fire_coroutines=fire_coroutines)
    
    obs_coroutines = show_obstacles(canvas, OBSTACLES)
    fill_orbit_coroutines = []

    coroutines = [
        blink(
            canvas,
            randint(1, canvas.getmaxyx()[0] - pading),
            randint(1, canvas.getmaxyx()[1] - pading),
            choice('★⚝✷*.○+●°•☆:☼❃')
        ) for num in range(50)]

    while True:
        if iter_count % 18 == 0:
            fill_orbit_coroutines.append(
                fill_orbit_with_garbage(
                    garbage_coroutine=fly_garbage(
                        canvas=canvas,
                        column=randint(1, canvas.getmaxyx()[1] - 3 * pading),
                        garbage_frame=choice(garbage_frames)
                    ),
                )
            )
        
        for fill_orbit_coroutine in fill_orbit_coroutines:
            try:
                fill_orbit_coroutine.send(None)
                obs_coroutines.send(None)
            except StopIteration:
                fill_orbit_coroutine.close()
            except RuntimeError:
                fill_orbit_coroutines.remove(fill_orbit_coroutine)
            finally:
                canvas.border()

        for num in range(len(coroutines)):
            coroutines[randint(0, len(coroutines)) - 1].send(None)

        for fire_coroutine in fire_coroutines:
            try:
                fire_coroutine.send(None)
            except StopIteration:
                fire_coroutine.close()
            except RuntimeError:
                fire_coroutine.close()
                fire_coroutines.remove(fire_coroutine)
            finally:
                canvas.border()

        rocket.send(None)
        canvas.refresh()
        iter_count += 1
        time.sleep(TIC_TIMEOUT)

    time.sleep(1)


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

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')

        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                collision_obstacles.append(obstacle)
                return
            
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, start_row, start_column, frames, fire_coroutines):
    frame_row, frame_column = get_frame_size(frames[0])
    row_speed = column_speed = 0
    for frame in cycle(frames):
        row, column, space = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed, row, column)

        if space:
            fire_coroutines.append(
                fire(
                    canvas=canvas,
                    start_row=start_row,
                    start_column=start_column + 2,
                    rows_speed=-1,
                )
            )

        if row_speed > 0:
            if (start_row + row_speed + frame_row) >= canvas.getmaxyx()[0]:
                start_row = canvas.getmaxyx()[0] - frame_row - 1

            else:
                start_row += row_speed

        if row_speed < 0:
            if (start_row + row_speed) <= 1:
                start_row = 1

            else:
                start_row += row_speed

        if column_speed > 0:
            if (start_column + column_speed + frame_column) >= canvas.getmaxyx()[1]:
                start_column = canvas.getmaxyx()[1] - frame_column - 1

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
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)
    rows_size, columns_size = get_frame_size(garbage_frame)
    row = 0

    obstacle = Obstacle(row, column, rows_size, columns_size)

    OBSTACLES.append(obstacle)

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed

        if obstacle in collision_obstacles:
            OBSTACLES.remove(obstacle)
            await explode(canvas, obstacle.row, obstacle.column)
            return
        
        else:
            obstacle.row += speed



async def fill_orbit_with_garbage(garbage_coroutine):
    while True:
        garbage_coroutine.send(None)
        await asyncio.sleep(0)

   
if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
