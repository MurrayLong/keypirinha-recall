# Keypirinha | A semantic launcher for Windows | http://keypirinha.com

import keypirinha as kp
import keypirinha_util as kpu
import sqlite3
import datetime

class Fact():
    def __init__(self, key, value):
        self.key = str(key)
        self.value = str(value)

class Recall(kp.Plugin):
    """Simple Key value pair database"""
    
    DEFAULT_DATABASE_FILE = None
    DEFAULT_ITEM_LABEL = "Recall"
    DEFAULT_ITEM_DESC = "Copy to clipboard"
    DEFAULT_ALWAYS_SUGGEST = False
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    DEFAULT_ITEM_LIMIT = 30
    KEYWORD = "fact"

    ADD_COMMAND_CATEGORY = kp.ItemCategory.USER_BASE+1
    DELETE_COMMAND_CATEGORY = kp.ItemCategory.USER_BASE+2
    SAVE_CATEGORY = kp.ItemCategory.USER_BASE+3
    DELETE_CATEGORY = kp.ItemCategory.USER_BASE+4
    
    database_file = DEFAULT_DATABASE_FILE
    
    facts=[]

    def __init__(self):
        super().__init__()
        self._debug = True # enables self.dbg() output
        self.dbg("CONSTRUCTOR")

    def on_start(self):
        self.dbg("Starting Facts Plugin")
        self.dbg("On Start")
        self._read_config()

    def on_catalog(self):
        self.dbg("On Catalog")
        self.facts = self._load_facts()
        self.set_catalog([self._create_keyword_item("Recall...",short_desc=self.DEFAULT_ITEM_DESC)])

    def on_suggest(self, user_input, items_chain):
        self.dbg('On Suggest "{}" (items_chain[{}])'.format(user_input, len(items_chain)))
        
        if items_chain and (
                items_chain[0].category() != kp.ItemCategory.KEYWORD or
                items_chain[0].target() != self.KEYWORD):
            return

        if (len(items_chain) > 1 and items_chain[1].category() == self.ADD_COMMAND_CATEGORY):
            if (len(items_chain) == 2 and user_input):
                self.set_suggestions([
                    self.create_item(
                        category=self.ADD_COMMAND_CATEGORY,
                        label=str(user_input),
                        short_desc=str(user_input),
                        target=str(user_input),
                        args_hint=kp.ItemArgsHint.REQUIRED,
                        hit_hint=kp.ItemHitHint.NOARGS
                    )], kp.Match.DEFAULT, kp.Sort.NONE)


            if (len(items_chain) == 3 and user_input):
                self.set_suggestions([
                    self.create_item(
                        category=self.SAVE_CATEGORY,
                        label=str(user_input),
                        short_desc=str(user_input),
                        target=str(user_input),
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.NOARGS,
                        data_bag = items_chain[2].label(),
                    )], kp.Match.DEFAULT, kp.Sort.NONE)
            return

        if (len(items_chain) > 1 and items_chain[1].category() == self.DELETE_COMMAND_CATEGORY):
            self.dbg("Displaying facts for deletion")
            deletables = []
            if not self.facts == None and not len(self.facts) == 0:
                for f in self.facts:
                    deletables.append(self._create_delete_action(f.key,f.value))
            self.set_suggestions(deletables, kp.Match.DEFAULT, kp.Sort.NONE)
            return


        deleteItem = self.create_item(
                category=self.DELETE_COMMAND_CATEGORY,
                label="Delete Entry",
                short_desc="Delete an entry",
                target="Delete Entry",
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE
            )

        addItem = self.create_item(
                category=self.ADD_COMMAND_CATEGORY,
                label="Add Entry",
                short_desc="Add a new entry",
                target="Add Entry",
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE
            )

        suggestions=[addItem, deleteItem]

        if not self.facts == None and not len(self.facts) == 0:
            for f in self.facts:
                suggestions.append(self._create_fact_item(f.key,f.value))

        self.set_suggestions(suggestions, kp.Match.DEFAULT, kp.Sort.NONE)

    def on_execute(self, item, action):
        self.dbg('On Execute "{}" (action: {})'.format(item, action))
        if not item:
            return
        if item.category() == kp.ItemCategory.EXPRESSION:
            kpu.set_clipboard(item.data_bag())
            return
        if item.category() == self.SAVE_CATEGORY:
            self._add_fact(Fact(item.data_bag(), item.label() ))
            self.facts = self._load_facts()
            return
        if item.category() == self.DELETE_CATEGORY:
            self._delete_fact(item.label())
            self.facts = self._load_facts()
            return

    def on_events(self, flags):
        self.dbg("On event(s) (flags {:#x})".format(flags))
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self.on_catalog()
        
    def _read_config(self):
        settings = self.load_settings()
        self.database_file = settings.get_stripped("database_file", "main", self.DEFAULT_DATABASE_FILE)
        
    def _create_keyword_item(self, label, short_desc):
        return self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label=label,
            short_desc=short_desc,
            target=self.KEYWORD,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
            )

    def _create_fact_item(self, key, value):
        return self.create_item(
            category=kp.ItemCategory.EXPRESSION,
            label=key,
            short_desc="{} (Press Enter to copy to clipboard)".format(value),
            target=str(key),
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.IGNORE,
            data_bag=str(value)
            )   

    def _create_delete_action(self, key, value):
        return self.create_item(
            category=self.DELETE_CATEGORY,
            label=key,
            short_desc="{} (Press Enter to delete)".format(value),
            target=str(key),
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.IGNORE,
            data_bag=str(value)
            )   
    
    def _db_init(self):
        try:
            connection = sqlite3.connect(self.database_file)
            c = connection.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS Facts (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT)")
            c.execute("INSERT INTO Facts VALUES(null,'Favourite Ice-cream flavour','Chocolate')")
            c.execute("INSERT INTO Facts VALUES(null,'Lottery Numbers','43,12,10,24,55')")
            c.execute("INSERT INTO Facts VALUES(null,'Wife''s birthday','3rd March')")
            c.execute("INSERT INTO Facts VALUES(null,'Licence Plate Number','JWD-334')")
            connection.commit()
            connection.close()
            self.dbg("Successfully initialised database file: " + self.database_file)
        except Exception as e:
            self.dbg("Unable to initialise database file: " + str(self.database_file)+" "+str(e))
    
    def _add_fact(self, fact):
        try:
            connection = sqlite3.connect(self.database_file)
            self.dbg("Saving {}:{}".format(fact.key, fact.value))
            c = connection.cursor()
            c.execute("INSERT INTO Facts VALUES(null,?,?)", (fact.key, fact.value))
            connection.commit()
            connection.close()
        except Exception as e:
            self.dbg("Unable to save to database"+str(e))

    def _delete_fact(self, key):
        try:
            connection = sqlite3.connect(self.database_file)
            self.dbg("Deleting "+key)
            c = connection.cursor()
            c.execute("DELETE FROM Facts WHERE key = ?", (str(key),))
            connection.commit()
            connection.close()
        except Exception as e:
            self.dbg("Unable to save to database: "+str(e))

    def _load_facts(self):
        try:
            connection = sqlite3.connect(self.database_file)
            c = connection.cursor()
            c.execute('SELECT * FROM Facts')
            self.dbg("Successfully loaded and read database file: " + self.database_file)
        except Exception as e:
            self.dbg("Unable to load database file: " + str(self.database_file)+": "+str(e))
            return

        clips = []
        for row in c.fetchall():
            self.dbg("Adding {}: {}".format(row[1],row[2]))
            clips.append(Fact(row[1],row[2]))
        
        return clips
