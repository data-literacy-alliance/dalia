(function () {
    'use strict';

    function initAnchors() {
        if (typeof anchors === 'undefined') { return; }
        anchors.options = {
            visible: 'hover',
            placement: 'right',
            truncate: 64
        };
        anchors.add('h1,h2,h3,h4');
    }

    function initWorkFieldTabs() {
        var tabs = document.getElementById('myTab');
        var pane = document.getElementById('tab1');
        if (!tabs || !pane) { return; }
        tabs.addEventListener('click', function (event) {
            var link = event.target.closest('[data-wp-body]');
            if (!link || !tabs.contains(link)) { return; }
            event.preventDefault();
            var template = document.getElementById(link.getAttribute('data-wp-body'));
            if (!template || !template.content) { return; }
            pane.textContent = '';
            pane.appendChild(template.content.cloneNode(true));
            tabs.querySelectorAll('[data-wp-body]').forEach(function (tab) {
                var isActive = tab === link;
                var icon = tab.querySelector('svg');
                tab.classList.toggle('active', isActive);
                if (icon) {
                    icon.classList.toggle('fill-white', isActive);
                    icon.classList.toggle('fill-blue', !isActive);
                }
            });
        });
    }

    // Replaces former inline on* handlers (CSP forbids inline scripts).
    function initDelegatedActions() {
        document.addEventListener('click', function (event) {
            var target = event.target.closest('[data-submenu-show],[data-submenu-hide],[data-toggle-x],[data-href]');
            if (!target) { return; }
            if (target.hasAttribute('data-submenu-show')) {
                showSubMenu(target.getAttribute('data-submenu-show'));
            } else if (target.hasAttribute('data-submenu-hide')) {
                hideSubMenu(target.getAttribute('data-submenu-hide'));
            } else if (target.hasAttribute('data-toggle-x')) {
                toggleX();
            } else {
                location.href = target.getAttribute('data-href');
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initAnchors();
        initWorkFieldTabs();
        initDelegatedActions();
    });
}());
