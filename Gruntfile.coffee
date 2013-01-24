# TODO: Differentiate this into production and dev configs.

module.exports = (grunt) ->
  grunt.initConfig
    pkg: grunt.file.readJSON 'package.json'
    copy:
      dist:
        files: [
          expand: true
          cwd: 'static-src/'
          src: '*'
          dest: 'static/'
          filter: 'isFile'
        ,
          # TODO: minify images?
          expand: true
          cwd: 'static-src/'
          src: 'img/*'
          dest: 'static/'
          filter: 'isFile'
        ,
          expand: true
          cwd: 'static-src/'
          src: 'font/*'
          dest: 'static/'
          filter: 'isFile'
        ]
    uglify:
      dist:
        files: [
          src: ['static-src/js/plugins.js',
            'static-src/js/bootstrap.js', 'static-src/js/main.js']
          dest: 'static/js/app.js'
        ,
          src: 'static-src/js/vendor/jquery-1.9.0.js'
          dest: 'static/js/vendor/jquery-1.9.0.min.js'
        ,
          src: 'static-src/js/vendor/modernizr-2.6.2.js'
          dest: 'static/js/vendor/modernizr-2.6.2.min.js'
        ]
    mincss:
      dist:
        files: [
          src: ['static-src/css/normalize.css',
            'static-src/css/main.css',
            'static-src/css/bootstrap.css',
            'static-src/css/bootstrap-responsive.css']
          dest: 'static/css/lib.min.css',
        ,
          src: 'static/css/app.css',
          dest: 'static/css/app.min.css'
        ]
    compass:
      dist:
        options:
          sassDir: 'static-src/sass'
          cssDir: 'static/css'
    watch:
      files: 'static-src/**/*'
      tasks: 'default'


  grunt.loadNpmTasks 'grunt-contrib-uglify'
  grunt.loadNpmTasks 'grunt-contrib-coffee'
  grunt.loadNpmTasks 'grunt-contrib-compass'
  grunt.loadNpmTasks 'grunt-contrib-watch'
  grunt.loadNpmTasks 'grunt-contrib-copy'
  grunt.loadNpmTasks 'grunt-contrib-mincss'

  grunt.registerTask 'default', ['copy', 'uglify', 'compass', 'mincss']
