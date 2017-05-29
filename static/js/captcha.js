$('.captcha-refresh, img.captcha').click(function(){
    var $form = $(this).parents('form');

    $.getJSON("/captcha/refresh/", {}, function(json) {
        $form.find('input[name="captcha_0"]').val(json.key);
        $form.find('img.captcha').attr('src', json.image_url);
    });

    return false;
});