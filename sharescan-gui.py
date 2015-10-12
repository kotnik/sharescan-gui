#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import base64
import urllib2
import Tkinter
import tkMessageBox
import subprocess
import multiprocessing


def http_get(url="", out=None):
    print "Getting %s" % url
    res = urllib2.urlopen(url).read()
    json_res = json.loads(res)
    print "Result: %s" % json_res
    out.put(json_res)
    return 0


def get_my_ip(out=None):
    site = urllib2.urlopen("http://checkip.dyndns.org/").read()
    grab = re.findall('([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', site)
    address = grab[0]
    print "My ip: %s" % address
    out.put(address)
    return 0


def http_post(url="", data={}, content_type="application/json", out=None):
    json_data = json.dumps(data)
    req = urllib2.Request(
        url,
        json_data,
        {"Content-Type": content_type}
    )
    try:
        f = urllib2.urlopen(req)
        out.put(f.getcode())
        f.close()
    except urllib2.HTTPError:
        out.put("Failed posting address")
        pass
    return 0


def run_traceroute(ip="", out=None):
    if not ip:
        out.set("ip not set")
        return 1

    output = subprocess.check_output(["traceroute", "-n", ip])
    print output
    out.put(base64.b64encode(output))


class SharescanGui(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.geometry("640x480")
        self.minsize(320, 240)
        self.initialize()

        self.started = False
        self.http_runner = None

    def initialize(self):
        self.grid()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text_area = Tkinter.Text(self, wrap=Tkinter.WORD)
        self.text_area.grid(
            column=0,
            row=0,
            columnspan=2,
            sticky=Tkinter.N + Tkinter.S + Tkinter.W + Tkinter.E
            )
        with open(os.path.join(os.path.dirname(__file__), 'INTRO.md')) as f:
            intro_text = f.read().strip()
        self._set_text(intro_text)

        self.start_button = Tkinter.Button(
            self,
            text=u"Start!",
            command=self.start_click,
            width=10,
            height=1,
            )
        self.start_button.grid(column=0, row=1)

        self.exit_button = Tkinter.Button(
            self,
            text=u"Exit",
            command=self.exit_click,
            width=10,
            height=1,
            )
        self.exit_button.grid(column=1, row=1)

        self.resizable(True, True)
        self.update()
        self.geometry(self.geometry())

    def _set_text(self, text):
        self.text_area.insert(Tkinter.END, text)
        self.text_area.see(Tkinter.END)

    def _run(self, fn, kwargs):
        self.http_runner = multiprocessing.Process(target=fn, kwargs=kwargs)
        self.http_runner.start()
        while self.http_runner.is_alive():
            self.update()
            time.sleep(0.1)

    def start_click(self):
        if self.started:
            return

        self.started = True
        out = multiprocessing.Queue()

        self._set_text(u"\n\n\nDobavljam svoju eksternu IP adresu...\n")
        self._run(get_my_ip, {"out": out})
        self.my_ip = out.get()

        self._set_text(u"\nŠaljem svoju IP adresu (%s)...\n" % self.my_ip)
        self._run(http_post, {
            "url": "https://shareforce.kotur.org/v1/ip/",
            "data": {"ip": self.my_ip},
            "out": out
        })
        print "Result: %s" % out.get()

        self._set_text(u"\nDobavljam sve IP adrese za skeniranje...\n")
        self._run(http_get, {
            "url": "https://shareforce.kotur.org/v1/ip/", "out": out
        })
        ips = out.get()
        self._set_text(u"\nSkeniranje adresa iz baze počinje...\n\n")
        if not ips:
            self._set_text(u"\nDesila se greška...\n")
            return

        for obj in ips["objects"]:
            ip = obj["ip"]
            if ip == self.my_ip:
                continue

            self._set_text(u"Skeniram %s...\n" % ip)
            self._run(run_traceroute, {"ip": ip, "out": out})
            trace = out.get()
            print "Posting %s" % trace
            self._run(http_post, {
                "url": "https://shareforce.kotur.org/v1/result/",
                "data": {
                    "source_ip": self.my_ip,
                    "destination_ip": ip,
                    "result": trace,
                },
                "out": out
            })
            print "Result: %s" % out.get()


        self._set_text(u"\nSkeniranje završeno. Hvala.\n")
        self.started = False

    def exit_click(self):
        if self.started:
            tkMessageBox.showinfo("Obaveštenje", "Molim sačekajte da se skeniranje završi...")
            return
        self.quit()


if __name__ == "__main__":
    app = SharescanGui(None)
    app.title(u"SHARE Scan GUI")
    app.mainloop()
