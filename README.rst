m
=

Lifecycle Example
-----------------

.. code-block:: bash

   $ cat ~/.bashrc

   lifecycle() {
     if [ "$#" == 1 ]; then
       command m ls ${1}
     elif [ "$2" = 'edit' ]; then
       command m edit "${1}/${3}"
     elif [ "$2" = 'rename' ]; then
       command m mv "${1}/${3}" "${1}/${4}"
     elif [ "$2" = 'mv' ]; then
       command m mv "${1}/${3}" "${3}/${4}"
     else
       command m cat "${1}/${2}"
     fi
   }

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
