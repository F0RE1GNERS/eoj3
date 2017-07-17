var gulp = require('gulp'),
    less = require('gulp-less'),
    cssmin = require('gulp-cssmin'),
    plumber = require('gulp-plumber'),
    rename = require('gulp-rename');

gulp.task('watch', function () {
  gulp.watch('./less/app.less', ['less-dev']);
});

gulp.task('less-dev', function() {
  gulp.src('./less/app.less')
    .pipe(less())
    .pipe(rename({
        suffix: '.min'
    }))
    .pipe(gulp.dest('./css'))
});

gulp.task('less', function () {
  gulp.src('./less/app.less')
    .pipe(plumber())
    .pipe(less())
    .pipe(gulp.dest('./css/'))
    .pipe(cssmin())
    .pipe(rename({
        suffix: '.min'
    }))
    .pipe(gulp.dest('./css'))
});

gulp.task('default', ['less', 'watch']);