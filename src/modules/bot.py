"""An interpreter that reads and executes user-created routines."""

import threading
import time

import cv2
import git

from src.command_book.command_book import CommandBook
from src.common import config, utils
from src.common.interfaces import Configurable
from src.common.vkeys import press
from src.routine.components import Point
from src.routine.routine import Routine
from src.runesolvercore.runesolver import enterCashshop
from src.runesolvercore.runesolver import solve_rune_raw

# The rune's buff icon
RUNE_BUFF_TEMPLATE = cv2.imread("assets/rune_buff_template.jpg", 0)


class Bot(Configurable):
    """A class that interprets and executes user-defined routines."""

    DEFAULT_CONFIG = {
        "NPC/Gather": "y",
        "Feed pet": "9",
        "Cash Shop": "`",
        "2x EXP Buff": "7",
        "Mushroom Buff": "8",
        "Additional EXP Buff": "9",
        "Gold Pot": "10",
        "Wealth Acquisition": "-",
    }

    def __init__(self):
        """Loads a user-defined routine on start up and initializes this Bot's main thread."""

        super().__init__("keybindings")
        config.bot = self

        self.rune_active = False
        self.rune_pos = (0, 0)
        self.rune_closest_pos = (0, 0)  # Location of the Point closest to rune
        self.rune_next_pos = (0, 0)
        self.submodules = []
        self.command_book = None  # CommandBook instanceq
        # self.module_name = None
        # self.buff = components.Buff()

        # self.command_book = {}
        # for c in (components.Wait, components.Walk, components.Fall,
        #           components.Move, components.Adjust, components.Buff):
        #     self.command_book[c.__name__.lower()] = c

        config.routine = Routine()

        self.hwnd = None

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

    def start(self):
        """
        Starts this Bot object's thread.
        :return:    None
        """

        # self.update_submodules()
        print("\n[~] Started main bot loop")
        self.thread.start()

    def _main(self):
        """
        The main body of Bot that executes the user's routine.
        :return:    None
        """

        self.ready = True
        config.listener.enabled = True
        last_fed = time.time()
        last_enteredCS = time.time()
        last_30m_expbuffed = None

        while True:
            if config.enabled and len(config.routine) > 0:
                # Buff and feed pets
                self.command_book.buff.main()
                pet_settings = config.gui.settings.pets
                auto_feed = pet_settings.auto_feed.get()
                num_pets = pet_settings.num_pets.get()

                # EXP Buff settings
                exp_buff_settings = config.gui.settings.expbuffsettings
                auto_buff_exp = exp_buff_settings.expbuff_use_toggle.get()
                expbuff_use_interval = exp_buff_settings.expbuff_use_interval.get()

                # CS reset settings
                misc_settings = config.gui.settings.miscsettings
                cs_reset_toggle = misc_settings.cs_reset_toggle.get()
                cs_reset_interval = misc_settings.cs_reset_interval.get()

                # feed pets
                now = time.time()
                if auto_feed and now - last_fed > 1200 / num_pets:
                    press(self.config["Feed pet"], 1)
                    last_fed = now

                # buff exp buff
                if auto_buff_exp:
                    if last_30m_expbuffed == None:
                        press(self.config["2x EXP Buff"], 1)
                        time.sleep(0.4)
                        press(self.config["Mushroom Buff"], 1)
                        time.sleep(0.4)
                        press(self.config["Additional EXP Buff"], 1)
                        time.sleep(0.4)
                        press(self.config["Gold Pot"], 1)
                        time.sleep(0.4)
                        press(self.config["Wealth Acquisition"], 1)
                        time.sleep(0.4)
                        last_30m_expbuffed = now
                    config.gui.view.monitoringconsole.set_nextexpbuffstat(
                        str(
                            round(
                                (
                                    expbuff_use_interval * 900
                                    - (now - last_30m_expbuffed)
                                )
                            )
                        )
                        + "s"
                    )
                    if now - last_30m_expbuffed > expbuff_use_interval * 900 + 10:
                        press(self.config["2x EXP Buff"], 1)
                        time.sleep(0.2)
                    if now - last_30m_expbuffed > 1800 + 10:
                        press(self.config["Mushroom Buff"], 1)
                        time.sleep(0.2)
                        press(self.config["Additional EXP Buff"], 1)
                        time.sleep(0.2)
                        press(self.config["Gold Pot"], 1)
                        time.sleep(0.2)
                        last_30m_expbuffed = now
                    if now - last_30m_expbuffed > 7200 + 10:
                        press(self.config["Wealth Acquisition"], 1)
                        time.sleep(0.2)
                        last_30m_expbuffed = now
                elif auto_buff_exp == False:
                    config.gui.view.monitoringconsole.set_nextexpbuffstat("Disabled")

                # Enter cash shop to reset DC timer
                config.gui.view.monitoringconsole.set_nextcsresetstat(
                    str(round((cs_reset_interval * 3600 - (now - last_enteredCS))))
                    + "s"
                )
                if cs_reset_toggle and now - last_enteredCS > cs_reset_interval * 3600:
                    print("Entering cash shop for reset")
                    enterCashshop(self)
                    last_enteredCS = now
                elif cs_reset_toggle == False:
                    config.gui.view.monitoringconsole.set_nextcsresetstat("Disabled")

                # Highlight the current Point
                config.gui.view.routine.select(config.routine.index)
                config.gui.view.details.display_info(config.routine.index)

                # Execute next Point in the routine
                element = config.routine[config.routine.index]
                if config.rune_cd == False:
                    if (
                        self.rune_active
                        and isinstance(element, Point)
                        and element.location == self.rune_closest_pos
                    ):
                        self._solve_rune()
                element.execute()
                config.routine.step()
            else:
                time.sleep(0.01)

    @utils.run_if_enabled
    def _solve_rune(self):
        """
        Moves to the position of the rune and solves the arrow-key puzzle.
        :param model:   The TensorFlow model to classify with.
        :return:        None
        """

        def move_to_rune(self):
            move = self.command_book["move"]
            move(*self.rune_pos).execute()
            adjust = self.command_book["adjust"]
            adjust(*self.rune_pos).execute()

        time.sleep(0.5)
        print("\nSolving rune:")
        solve_rune_raw(self, self, move_to_rune=move_to_rune)
        self.rune_active = False

    def load_commands(self, file):
        try:
            self.command_book = CommandBook(file)
            config.gui.settings.update_class_bindings()
        except ValueError:
            pass  # TODO: UI warning popup, say check cmd for errors
        #
        # utils.print_separator()
        # print(f"[~] Loading command book '{basename(file)}':")
        #
        # ext = splitext(file)[1]
        # if ext != '.py':
        #     print(f" !  '{ext}' is not a supported file extension.")
        #     return False
        #
        # new_step = components.step
        # new_cb = {}
        # for c in (components.Wait, components.Walk, components.Fall):
        #     new_cb[c.__name__.lower()] = c
        #
        # # Import the desired command book file
        # module_name = splitext(basename(file))[0]
        # target = '.'.join(['resources', 'command_books', module_name])
        # try:
        #     module = importlib.import_module(target)
        #     module = importlib.reload(module)
        # except ImportError:     # Display errors in the target Command Book
        #     print(' !  Errors during compilation:\n')
        #     for line in traceback.format_exc().split('\n'):
        #         line = line.rstrip()
        #         if line:
        #             print(' ' * 4 + line)
        #     print(f"\n !  Command book '{module_name}' was not loaded")
        #     return
        #
        # # Check if the 'step' function has been implemented
        # step_found = False
        # for name, func in inspect.getmembers(module, inspect.isfunction):
        #     if name.lower() == 'step':
        #         step_found = True
        #         new_step = func
        #
        # # Populate the new command book
        # for name, command in inspect.getmembers(module, inspect.isclass):
        #     new_cb[name.lower()] = command
        #
        # # Check if required commands have been implemented and overridden
        # required_found = True
        # for command in [components.Buff]:
        #     name = command.__name__.lower()
        #     if name not in new_cb:
        #         required_found = False
        #         new_cb[name] = command
        #         print(f" !  Error: Must implement required command '{name}'.")
        #
        # # Look for overridden movement commands
        # movement_found = True
        # for command in (components.Move, components.Adjust):
        #     name = command.__name__.lower()
        #     if name not in new_cb:
        #         movement_found = False
        #         new_cb[name] = command
        #
        # if not step_found and not movement_found:
        #     print(f" !  Error: Must either implement both 'Move' and 'Adjust' commands, "
        #           f"or the function 'step'")
        # if required_found and (step_found or movement_found):
        #     self.module_name = module_name
        #     self.command_book = new_cb
        #     self.buff = new_cb['buff']()
        #     components.step = new_step
        #     config.gui.menu.file.enable_routine_state()
        #     config.gui.view.status.set_cb(basename(file))
        #     config.routine.clear()
        #     print(f" ~  Successfully loaded command book '{module_name}'")
        # else:
        #     print(f" !  Command book '{module_name}' was not loaded")

    def update_submodules(self, force=False):
        """
        Pulls updates from the submodule repositories. If FORCE is True,
        rebuilds submodules by overwriting all local changes.
        """

        utils.print_separator()
        print("[~] Retrieving latest submodules:")
        self.submodules = []
        repo = git.Repo.init()
        with open(".gitmodules", "r") as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("[") and i < len(lines) - 2:
                    path = lines[i + 1].split("=")[1].strip()
                    url = lines[i + 2].split("=")[1].strip()
                    self.submodules.append(path)
                    try:
                        repo.git.clone(url, path)  # First time loading submodule
                        print(f" -  Initialized submodule '{path}'")
                    except git.exc.GitCommandError:
                        sub_repo = git.Repo(path)
                        if not force:
                            sub_repo.git.stash()  # Save modified content
                        sub_repo.git.fetch("origin", "main")
                        sub_repo.git.reset("--hard", "FETCH_HEAD")
                        if not force:
                            try:  # Restore modified content
                                sub_repo.git.checkout("stash", "--", ".")
                                print(
                                    f" -  Updated submodule '{path}', restored local changes"
                                )
                            except git.exc.GitCommandError:
                                print(f" -  Updated submodule '{path}'")
                        else:
                            print(f" -  Rebuilt submodule '{path}'")
                        sub_repo.git.stash("clear")
                    i += 3
                else:
                    i += 1
