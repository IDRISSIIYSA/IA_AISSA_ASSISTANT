"""Ressources partagées entre les pages : secrets et mémoire durable (avec les cerveaux révisés)."""

import os

import streamlit as st

from .corrections import brancher
from .memoire import Memoire


def secret(nom):
    try:
        return st.secrets.get(nom) or os.environ.get(nom)
    except Exception:
        return os.environ.get(nom)


@st.cache_resource(show_spinner=False)
def memoire():
    m = Memoire(secret("MEMOIRE_URL"))
    brancher(m)
    return m
