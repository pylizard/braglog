import os
import sqlite3
import objc

from AppKit import (
    NSApplication,
    NSApp,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSMenu,
    NSMenuItem,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSViewController,
    NSView,
    NSTextField,
    NSButton,
    NSMinYEdge,
    NSUserNotification,
    NSTextView,
    NSScrollView,
    NSMakeRect,
    NSBezelBorder,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

DB_PATH = "./log.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                project TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

# ——————— View Controller for the popover ————————

class EntryViewController(NSViewController):

    def loadView(self):
        width, height = 400, 180
        v = NSView.alloc().initWithFrame_(((0, 0), (width, height)))

        def make_text_area(y_offset):
            scroll = NSScrollView.alloc().initWithFrame_(((10, y_offset), (width - 20, 80)))
            scroll.setHasVerticalScroller_(True)
            scroll.setBorderType_(NSBezelBorder)
            scroll.setAutohidesScrollers_(True)

            text_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, width - 20, 80))
            text_view.setVerticallyResizable_(True)
            text_view.setHorizontallyResizable_(False)
            scroll.setDocumentView_(text_view)
            return scroll, text_view

        # Message area
        self.scroll1, self.textView = make_text_area(height - 100)
        self.textView.setPlaceholderString_("Main log entry")
        self.textView.setRichText_(True)
        self.textView.setEditable_(True)
        self.textView.setSelectable_(True)
        self.textView.setAllowsUndo_(True)

        v.addSubview_(self.scroll1)

        # Project field
        self.projectField = NSTextField.alloc().initWithFrame_(((10, height - 130), (width - 20, 24)))
        self.projectField.setPlaceholderString_("Optional project tag")
        v.addSubview_(self.projectField)

        # Save button, now pulled up
        btn = NSButton.alloc().initWithFrame_(((width - 80, 10), (70, 30)))
        btn.setTitle_("Save")
        btn.setBezelStyle_(1)
        btn.setKeyEquivalent_("\r")
        btn.setTarget_(self)
        btn.setAction_("saveEntry:")
        v.addSubview_(btn)

        self.setView_(v)

    @objc.IBAction
    def saveEntry_(self, sender):
        msg = self.textView.string().strip()
        project = self.projectField.stringValue().strip() or None
        print(f"{project or ''}::{msg}")

        if msg:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO logs (message, project) VALUES (?, ?)",
                    (msg, project)
                )

        self.textView.setString_("")
        self.projectField.setStringValue_("")
        self.popover.performClose_(None)

    # Register with PyObjC runtime
    saveEntry_ = objc.selector(saveEntry_, signature=b'v@:@')


# ——————— App Delegate ————————

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        init_db()

        # ——————— Main Menu (for global ⌘C/⌘V support) ———————
        mainMenu = NSMenu.alloc().init()
        appMenuItem = NSMenuItem.alloc().init()  # Dummy slot for application menu
        mainMenu.addItem_(appMenuItem)

        editMenu = NSMenu.alloc().initWithTitle_("Edit")
        for title, action, key in [
            ("Undo", "undo:", "z"),
            ("Redo", "redo:", "Z"),
            (None, None, None),
            ("Cut", "cut:", "x"),
            ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"),
            ("Select All", "selectAll:", "a"),
        ]:
            if title is None:
                editMenu.addItem_(NSMenuItem.separatorItem())
            else:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
                editMenu.addItem_(item)

        editMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", "", "")
        editMenuItem.setSubmenu_(editMenu)
        mainMenu.addItem_(editMenuItem)

        NSApp.setMainMenu_(mainMenu)

        # ——————— Status Bar Icon + Menu ———————
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)
        self.statusItem.button().setTitle_("BragLog")

        statusMenu = NSMenu.alloc().init()

        newItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("New Entry",
                                                                         "togglePopover:", "n")
        newItem.setTarget_(self)
        statusMenu.addItem_(newItem)

        statusMenu.addItem_(NSMenuItem.separatorItem())

        quitItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
        quitItem.setTarget_(NSApp)
        statusMenu.addItem_(quitItem)

        self.statusItem.setMenu_(statusMenu)

        # ——————— Popover + Entry ViewController ———————
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(NSPopoverBehaviorTransient)
        self.popover.setAppearance_(self.statusItem.button().window().appearance())

        self.vc = EntryViewController.alloc().init()
        self.vc.popover = self.popover
        self.popover.setContentViewController_(self.vc)

    @objc.IBAction
    def togglePopover_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(sender)
        else:
            # Ensure app is frontmost so field can get focus
            NSApp.activateIgnoringOtherApps_(True)

            button = self.statusItem.button()
            self.popover.showRelativeToRect_ofView_preferredEdge_(
                button.bounds(),
                button,
                NSMinYEdge
            )

            # Focus the text field on next run loop turn
            AppHelper.callLater(0.01, lambda: self.vc.textView.window().makeFirstResponder_(self.vc.textView))


if __name__ == "__main__":
    init_db()
    objc.options.verbose = 1  # to see Objective-C traceback
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
