m
=


Available Commands
------------------

.. code-block:: bash

   $ m --help

   Usage: m [OPTIONS] COMMAND [ARGS]...

   Options:
     -h, --host TEXT
     -n, --namespace TEXT
     --version             Show the version and exit.
     --help                Show this message and exit.

   Commands:
     edit
     history
     login
     ls
     mv
     open
     rm
     upload


Usage
-----

.. code-block:: bash

   $ m login google

   $ m upload hello/world <(echo "hello world")
   a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447-12

   $ m ls
   2021-01-18 a948904f2 hello/world

   $ m open hello/world
   hello world

   $ m edit hello/world
   f750b886d6e786f7e238e232b54194c6e24625c47755bd87a396211b5f1a4316-18

   $ m history hello/world
   2021-01-18 f750b886d
   2021-01-18 a948904f2

   $ m open hello/world
   hello world again

   $ m mv hello/world tasks/todo/first-task
   a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447-12
   f750b886d6e786f7e238e232b54194c6e24625c47755bd87a396211b5f1a4316-18

   $ m history tasks/todo/first-task
   2021-01-18 f750b886d
   2021-01-18 a948904f2

   $ m upload gotoapp/shortlinks/google https://google.com
   e70c48da01df540a8c2941ca58d38f80521912d24654caa45f0de49523454c73-76

   $ m upload gotoapp/shortlinks/youtube https://youtube.com
   8e95412bfd03b66541b5f208b86e7001f2aa1d7c211796e4972ce103cb9bcef7-77

   $ m -n gotoapp/shortlinks ls
   2021-01-18 8e95412bf youtube
   2021-01-18 e70c48da0 google

   $ m open youtube

   $ m rm youtube


Lifecycle Example
-----------------

.. code-block:: bash

   $ cat ~/.bashrc

   lifecycle() {
     if [ "$#" == 1 ]; then
       command m ls ${1}
     elif [ "$2" = 'new' ]; then
       command m upload "${1}/${3}" $4
     elif [ "$2" = 'edit' ]; then
       command m edit "${1}/${3}"
     elif [ "$2" = 'rename' ]; then
       command m mv "${1}/${3}" "${1}/${4}"
     elif [ "$2" = 'mv' ]; then
       command m mv "${1}/${3}" "${3}/${4}"
     else
       command m open "${1}/${2}"
     fi
   }

   alias gotoapp='M_NAMESPACE=gotoapp/shortlinks lifecycle'
   alias goto='gotoapp shortlinks'

   alias taskapp='M_NAMESPACE=taskapp/tasks lifecycle'
   alias tasks='taskapp tasks'
   alias today='taskapp today'
   alias todo='taskapp todo'
   alias later='taskapp later'
   alias blocked='taskapp blocked'
   alias taskarchive='M_NAMESPACE=taskapp m mv tasks/done archive'

   alias blogapp='M_NAMESPACE=blogapp/posts lifecycle'
   alias blog='blogapp blog'
   alias drafts='blogapp drafts'
   alias blogarchive='M_NAMESPACE=blogapp m mv blog/published archive'
