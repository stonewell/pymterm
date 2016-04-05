import blessed
import colorama

colorama.init()
t = blessed.Terminal()

print colorama.Fore.RED
print t.bold_red_on_bright_green('It hurts my eyes!')
print colorama.Fore.RESET
