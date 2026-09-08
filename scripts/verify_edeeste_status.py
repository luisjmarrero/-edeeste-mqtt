#!/usr/bin/env python3
"""Verify EDEEste login and consumption retrieval without Home Assistant."""

from __future__ import annotations

import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser


LOGIN_URL = "https://oficinavirtual.edeeste.com.do/Login.aspx?ReturnUrl=%2F"
SERVICE_STATUS_URL = (
    "https://oficinavirtual.edeeste.com.do/EstadoCircuito.aspx/GetEstadoCircuito"
)


class HiddenInputParser(HTMLParser):
    """Extract ASP.NET state fields from a form page."""

    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if (
            tag == "input"
            and attributes.get("type") == "hidden"
            and attributes.get("name")
        ):
            self.values[attributes["name"]] = attributes.get("value", "")


def main() -> int:
    """Log in and print the data from the authenticated endpoint."""
    email = input("EDEEste email: ").strip()
    password = getpass.getpass("EDEEste password: ")
    nic = input("EDEEste NIC: ").strip()
    if not email or not password or not nic:
        print("Email, password and NIC are required.", file=sys.stderr)
        return 2

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    try:
        with opener.open(LOGIN_URL, timeout=30) as response:
            parser = HiddenInputParser()
            parser.feed(response.read().decode("utf-8"))
        if "__VIEWSTATE" not in parser.values:
            print("Could not find EDEEste's ASP.NET login form state.", file=sys.stderr)
            return 1

        parser.values.update(
            {
                "ctl00$ContentPlaceHolder1$ucLogin$TxtUsuario": email,
                "ctl00$ContentPlaceHolder1$ucLogin$TxtPassword": password,
                "ctl00$ContentPlaceHolder1$ucLogin$BtnLogin": "Iniciar sesión",
            }
        )
        request = urllib.request.Request(
            LOGIN_URL,
            data=urllib.parse.urlencode(parser.values).encode(),
            method="POST",
        )
        with opener.open(request, timeout=30) as response:
            if "Login.aspx" in response.url:
                print("Login failed. Check the email and password.", file=sys.stderr)
                return 1

        request = urllib.request.Request(
            SERVICE_STATUS_URL,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json; charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
            },
            data=json.dumps({"nic": nic}).encode(),
        )
        with opener.open(request, timeout=30) as response:
            body = response.read()
            if "Login.aspx" in response.url:
                print(
                    "EDEEste redirected back to login after authentication.",
                    file=sys.stderr,
                )
                return 1
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                content_type = response.headers.get("Content-Type", "unknown")
                preview = body.decode("utf-8", errors="replace")[:160].replace(
                    "\n", " "
                )
                print(
                    "EDEEste returned a non-JSON consumption response "
                    f"(status {response.status}, URL {response.url}, type {content_type}): {preview!r}",
                    file=sys.stderr,
                )
                return 1
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        print(f"EDEEste HTTP error {err.code}: {body[:200]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as err:
        print(f"EDEEste URL error: {err}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as err:
        print(f"EDEEste JSON decode error: {err}", file=sys.stderr)
        return 1

    data = payload.get("d")
    if not data:
        print("Login succeeded but no consumption data was returned.", file=sys.stderr)
        return 1
    print("Login and data retrieval succeeded.")

    nic = data.get("Nic", "")
    sin_incidencia = data.get("SinIncidencia", False)
    error = data.get("Error", False)
    mensaje = data.get("Mensaje", "")

    result = {
        "nic": nic,
        "sin_incidencia": sin_incidencia,
        "error": error,
    }
    if mensaje:
        result["mensaje"] = mensaje

    print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
