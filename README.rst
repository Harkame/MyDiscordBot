MYDiscordBot
============

|Codacy Badge| |License: GPL v3| |Build Status|

Inspired by
-----------
-  `eviipy_bot`_

Installation
------------

.. code:: bash

   pip install -r requirements.txt -U

Dependencies
~~~~~~~~~~~~

-  `PyYAML`_

-  `lxml`_

Heroku
------

Create an config var : DISCORD_BOT_TOKEN <my_discord_bot_token>

Edit Procfile if necessary

Usage
-----

Run
~~~

.. code:: bash

   python mydiscordbot/main.py -t my_token

Options
~~~~~~~

.. code:: bash

  TODO

How it work
~~~~~~~~~~~

This program use an config file (default : ./config.yml)

TODO

.. _PyYAML: https://github.com/yml/pyyml
.. _lxml: https://github.com/lxml/lxml.git
.. _eviipy_bot: https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34

.. |Codacy Badge| image:: https://api.codacy.com/project/badge/Grade/a2edf760e13546db92ed8e0d6537161a
   :target: https://www.codacy.com/app/Harkame/MyDiscordBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Harkame/MyDiscordBot&amp;utm_campaign=Badge_Grade
.. |License: GPL v3| image:: https://img.shields.io/badge/License-GPLv3-blue.svg
   :target: https://www.gnu.org/licenses/gpl-3.0
.. |Build Status| image:: https://travis-ci.org/Harkame/MyDiscordBot.svg?branch=master
   :target: https://travis-ci.org/Harkame/MyDiscordBot
