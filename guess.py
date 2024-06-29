import random 
import streamlit as st

def guess(x):
    random_number = random.randint(1,x)
    guess = 0

    while guess != random_number:
        guess = int(input(f'Guess a number between 1 and {x}: '))
        if guess > random_number:
            print("Sorry, guess again. Too high.")
        elif guess < random_number:
            print("Sorry, guess again. Too low.")
        else:
            print(f'Yay, congrats. You have guessed the number {random_number} correctly!!')
            break

guess(10)


st.title("guess with me!!")
