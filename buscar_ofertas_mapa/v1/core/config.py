import json
import re

with open("config.json", "r", encoding="utf-8") as file:
    data = json.load(file)

countries = data.get("countries")
default_country = data["countries"].get("Iceland", next(iter(data["countries"].values())))
false_ends = data.get("false_ends")
headers = data.get("headers")

social_blacklist = data.get("social_blacklist")
generic_email_domains = data.get("generic_email_domains")

email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
mailto_regex = re.compile(r"mailto:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", re.IGNORECASE)
phone_regex = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
tel_regex = re.compile(r"tel:\s*(\+?\d[\d\s().-]{5,}\d)", re.IGNORECASE)
ig_regex = re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE)
fb_regex = re.compile(r"https?://(?:www\.|m\.)?facebook\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE)
li_regex = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9._-]+/?", re.IGNORECASE)
