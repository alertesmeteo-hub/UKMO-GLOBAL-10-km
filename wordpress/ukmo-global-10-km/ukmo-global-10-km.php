<?php
/**
 * Plugin Name: UKMO Global 10 km — Prévisions communales
 * Plugin URI: https://github.com/alertesmeteo-hub/UKMO-GLOBAL-10-km
 * Description: Prévisions horaires de pluie UKMO Global 10 km du Met Office pour l’Occitanie et la région PACA.
 * Version: 2.0.0
 * Author: Alertes Météo Hub
 * Requires at least: 5.8
 * Requires PHP: 7.4
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

define('UKMOG_VERSION', '2.0.0');
define('UKMOG_RELEASE_DATE', '26/09/2026');
define('UKMOG_OPTION_BASE_URL', 'ukmog_national_data_base_url');
define(
    'UKMOG_DEFAULT_BASE_URL',
    'https://raw.githubusercontent.com/alertesmeteo-hub/UKMO-GLOBAL-10-km/data'
);

add_action('wp_enqueue_scripts', 'ukmog_register_assets');
add_action('admin_init', 'ukmog_register_settings');
add_action('admin_menu', 'ukmog_add_settings_page');
add_shortcode('ukmo_global_meteo', 'ukmog_render_shortcode');
add_filter('plugin_action_links_' . plugin_basename(__FILE__), 'ukmog_plugin_action_links');

function ukmog_plugin_action_links($links) {
    $settings_link = sprintf(
        '<a href="%s">%s</a>',
        esc_url(admin_url('options-general.php?page=ukmo-global-10-km')),
        esc_html__('Réglages', 'ukmo-global-10-km')
    );
    array_unshift($links, $settings_link);

    $help_link = sprintf(
        '<a href="%s">%s</a>',
        esc_url(admin_url('options-general.php?page=ukmo-global-10-km')),
        esc_html__('Shortcodes / Aide', 'ukmo-global-10-km')
    );
    array_unshift($links, $help_link);

    return $links;
}

function ukmog_register_assets() {
    wp_register_style('ukmog-maps', plugin_dir_url(__FILE__) . 'assets/ukmo-maps.css', array('ukmog-table'), UKMOG_VERSION);
    wp_register_script('ukmog-vector', plugin_dir_url(__FILE__) . 'assets/icon-vector-zoom.js', array(), UKMOG_VERSION, true);
    wp_register_script('ukmog-maps', plugin_dir_url(__FILE__) . 'assets/ukmo-maps.js', array('ukmog-vector'), UKMOG_VERSION, true);
    wp_register_style(
        'ukmog-table',
        plugin_dir_url(__FILE__) . 'assets/arome-meteo.css',
        array(),
        UKMOG_VERSION
    );
    wp_register_script(
        'ukmog-table',
        plugin_dir_url(__FILE__) . 'assets/arome-meteo.js',
        array(),
        UKMOG_VERSION,
        true
    );

}

function ukmog_register_settings() {
    register_setting(
        'ukmog_settings',
        UKMOG_OPTION_BASE_URL,
        array(
            'type' => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default' => UKMOG_DEFAULT_BASE_URL,
        )
    );

    add_settings_section(
        'ukmog_main_section',
        'Source des données nationales',
        '__return_false',
        'ukmo-global-10-km'
    );

    add_settings_field(
        'ukmog_data_base_url_field',
        'Adresse du dossier de données',
        'ukmog_render_url_field',
        'ukmo-global-10-km',
        'ukmog_main_section'
    );
}

function ukmog_render_url_field() {
    $value = get_option(UKMOG_OPTION_BASE_URL, UKMOG_DEFAULT_BASE_URL);
    printf(
        '<input type="url" class="regular-text code" name="%1$s" value="%2$s" autocomplete="off">',
        esc_attr(UKMOG_OPTION_BASE_URL),
        esc_attr($value)
    );
    echo '<p class="description">Conservez l’adresse proposée : elle pointe vers la branche nationale « data » du dépôt.</p>';
}

function ukmog_add_settings_page() {
    add_options_page(
        'Tableau UKMO Global 10 km',
        'UKMO Global Met Office',
        'manage_options',
        'ukmo-global-10-km',
        'ukmog_render_settings_page'
    );
}

function ukmog_render_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    ?>
    <div class="wrap">
        <h1>UKMO Global 10 km</h1>
        <form action="options.php" method="post">
            <?php
            settings_fields('ukmog_settings');
            do_settings_sections('ukmo-global-10-km');
            submit_button();
            ?>
        </form>
        <p><strong>Version du module : <?php echo esc_html(UKMOG_VERSION); ?> (<?php echo esc_html(UKMOG_RELEASE_DATE); ?>)</strong></p>
        <h2>Shortcode unique</h2>
        <p><code>[ukmo_global_meteo]</code> : pluie horaire et cumulée jusqu’à +168 h.</p>
        <p><code>[ukmo_global_meteo code="34172" departement="34" ville="Montpellier" heures="168"]</code></p>
        <p><code>[ukmo_global_meteo code="66136" departement="66" ville="Perpignan" selecteur="non"]</code> : une seule ville, sans recherche.</p>
        <p>Le visiteur peut rechercher une commune d’Occitanie ou de Provence-Alpes-Côte d’Azur, ou saisir son code postal.</p>
    </div>
    <?php
}

function ukmog_base_url() {
    $url = get_option(UKMOG_OPTION_BASE_URL, UKMOG_DEFAULT_BASE_URL);
    return untrailingslashit(apply_filters('ukmog_national_data_base_url', $url));
}

function ukmog_department_code($value) {
    $code = strtoupper(trim((string) $value));
    return preg_match('/^(?:\d{2}|2A|2B)$/', $code) ? $code : '66';
}

function ukmog_commune_code($value) {
    $code = strtoupper(trim((string) $value));
    return preg_match('/^[0-9A-Z]{5}$/', $code) ? $code : '66136';
}

function ukmog_unique_identifier() {
    if (function_exists('wp_unique_id')) {
        return wp_unique_id('ukmog-city-');
    }
    return 'ukmog-city-' . wp_rand(1000, 999999);
}

function ukmog_render_shortcode($atts) {
    $atts = shortcode_atts(
        array(
            'ville' => 'Perpignan',
            'code' => '66136',
            'departement' => '66',
            'heures' => '168',
            'titre' => '',
            'selecteur' => 'oui',
        ),
        $atts,
        'ukmo_global_meteo'
    );

    $hours = max(1, min(168, absint($atts['heures'])));
    $city_name = sanitize_text_field($atts['ville']);
    if ($city_name === '') {
        $city_name = 'Perpignan';
    }
    $city_code = ukmog_commune_code($atts['code']);
    $department = ukmog_department_code($atts['departement']);
    $title_prefix = trim(sanitize_text_field($atts['titre']));
    if ($title_prefix === '') {
        $title_prefix = 'Prévisions UKMO Global';
    }
    $selector_value = strtolower(trim(sanitize_text_field($atts['selecteur'])));
    $show_selector = !in_array($selector_value, array('non', '0', 'false', 'off'), true);

    $input_id = ukmog_unique_identifier();
    $results_id = $input_id . '-results';
    $status_id = $input_id . '-status';

    wp_enqueue_style('ukmog-table');
    wp_enqueue_script('ukmog-table');
    wp_enqueue_script('ukmog-maps');
    wp_enqueue_style('ukmog-maps');

    ob_start();
    ?>
    <section
        class="ukmog-card ukmog-national"
        data-ukmog-app
        data-base-url="<?php echo esc_url(ukmog_base_url()); ?>"
        data-default-code="<?php echo esc_attr($city_code); ?>"
        data-default-department="<?php echo esc_attr($department); ?>"
        data-default-name="<?php echo esc_attr($city_name); ?>"
        data-hours="<?php echo esc_attr($hours); ?>"
        data-timezone="<?php echo esc_attr(wp_timezone_string()); ?>"
        data-title-prefix="<?php echo esc_attr($title_prefix); ?>"
        data-selector="<?php echo $show_selector ? '1' : '0'; ?>"
    >
        <header class="ukmog-header">
            <div>
                <p class="ukmog-kicker">PLUIE HORAIRE • OCCITANIE ET PACA</p>
                <h2 data-ukmog-title><?php echo esc_html($title_prefix . ' — ' . $city_name); ?></h2>
                <p class="ukmog-city-altitude" data-ukmog-altitude>Altitude de <?php echo esc_html($city_name); ?> : chargement…</p>
                <p class="ukmog-meta" data-ukmog-meta>Chargement du dernier run UKMO Global…</p>
            </div>
            <div class="ukmog-badge">UKMO Global<br><strong>10 km</strong></div>
        </header>

        <div class="ukmog-toolbar" <?php if (!$show_selector) : ?>hidden<?php endif; ?>>
            <div class="ukmog-search">
                <label for="<?php echo esc_attr($input_id); ?>">Choisissez votre commune</label>
                <div class="ukmog-search-control">
                    <span class="ukmog-search-icon" aria-hidden="true">⌕</span>
                    <input
                        id="<?php echo esc_attr($input_id); ?>"
                        class="ukmog-city-input"
                        type="search"
                        value="<?php echo esc_attr($city_name); ?>"
                        placeholder="Nom de commune ou code postal"
                        autocomplete="off"
                        spellcheck="false"
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded="false"
                        aria-controls="<?php echo esc_attr($results_id); ?>"
                        aria-describedby="<?php echo esc_attr($status_id); ?>"
                    >
                </div>
                <button type="button" class="ukmog-locate-button" data-ukmog-locate>📍 Détecter ma ville</button>
                <div
                    id="<?php echo esc_attr($results_id); ?>"
                    class="ukmog-search-results"
                    role="listbox"
                    hidden
                ></div>
                <p
                    id="<?php echo esc_attr($status_id); ?>"
                    class="ukmog-search-status"
                    role="status"
                    aria-live="polite"
                >Saisissez au moins deux lettres ou un code postal.</p>
            </div>
            <div class="ukmog-coverage">
                <strong>5 392 communes</strong>
                <span>Occitanie et PACA • 19 départements</span>
            </div>
        </div>

        <p class="ukmog-stale" data-ukmog-stale role="status" hidden>
            Attention : la dernière mise à jour disponible a plus de 8 heures.
        </p>

        <p>Cartes France/Europe jusqu’à +168 h : température à 1,5 m, précipitations cumulées, vent, rafales maximales et nuages. Les tableaux communaux restent limités à la pluie en Occitanie et PACA.</p>
        <div class="ukmog-tabs" role="tablist" aria-label="Cartes et tableaux UKMO">
            <button type="button" class="ukmog-tab is-active" role="tab" aria-selected="true" data-ukmog-tab="map-fixed">Europe/France</button>
            <button type="button" class="ukmog-tab" role="tab" aria-selected="false" data-ukmog-tab="map-france">France Zoom interactif</button>
            <button type="button" class="ukmog-tab" role="tab" aria-selected="false" data-ukmog-tab="map-europe">Europe Zoom interactif</button>
            <span class="ukmog-table-label">TABLEAU :</span>
            <button type="button" class="ukmog-tab" role="tab" aria-selected="false" data-ukmog-tab="general">Pluie · Occitanie/PACA</button>
        </div>

        <?php foreach (array('map-fixed' => array('france', '1'), 'map-france' => array('france', '0'), 'map-europe' => array('europe', '0')) as $map_view => $map_config) : ?>
        <section class="ukmog-panel ukmog-map-panel" data-ukmog-panel="<?php echo esc_attr($map_view); ?>" <?php if ($map_view !== 'map-fixed') : ?>hidden<?php endif; ?>>
            <div class="ukmog-map-widget" data-ukmog-map data-region="<?php echo esc_attr($map_config[0]); ?>" data-fixed="<?php echo esc_attr($map_config[1]); ?>">
                <div class="ukmog-map-tools">
                    <div class="ukmog-map-products" aria-label="Paramètre météo"></div>
                    <?php if ($map_config[1] === '1') : ?><div class="ukmog-map-regions"><button type="button" data-region="france" aria-pressed="true">France</button><button type="button" data-region="europe" aria-pressed="false">Europe</button></div><?php endif; ?>
                    <div class="ukmog-map-leads" aria-label="Échéance"></div>
                </div>
                <p class="ukmog-map-summary"></p>
                <div class="ukmog-map-viewer">
                    <img class="ukmog-map-image" alt="Carte UKMO Global 10 km">
                    <div class="ukmog-map-probe" hidden><strong></strong><span></span></div>
                    <?php if ($map_config[1] === '0') : ?><div class="ukmog-map-zoom"><button type="button" data-zoom="in">+</button><button type="button" data-zoom="out">−</button><button type="button" data-zoom="reset">⌂</button></div><?php endif; ?>
                    <p class="ukmog-map-status" role="status">Chargement de la carte…</p>
                </div>
            </div>
        </section>
        <?php endforeach; ?>

        <div class="ukmog-panel" data-ukmog-panel="general" hidden>
            <div class="ukmog-table-wrap ukmog-general-wrap" role="region" aria-label="Prévisions horaires générales" tabindex="0">
                <table class="ukmog-table">
                    <thead>
                        <tr>
                            <th scope="col">Date</th>
                            <th scope="col">Heure</th>
                            <th scope="col">Temps</th>
                            <th scope="col">T°</th>
                            <th scope="col">Hum.</th>
                            <th scope="col">Pluie</th>
                            <th scope="col">Nuages</th>
                            <th scope="col">Vent</th>
                            <th scope="col">Rafales</th>
                            <th scope="col">Pression</th>
                        </tr>
                    </thead>
                    <tbody data-ukmog-body-general>
                        <tr>
                            <td colspan="10" class="ukmog-loading">Chargement des prévisions…</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <section class="ukmog-charts" data-ukmog-charts aria-label="Diagrammes UKMO Global">
                <article class="ukmog-chart-card">
                    <h3 data-ukmog-chart-title-temperature>Diagramme températures (°C)</h3>
                    <div class="ukmog-chart" data-ukmog-chart-temperature></div>
                </article>
                <article class="ukmog-chart-card">
                    <h3 data-ukmog-chart-title-pressure>Diagramme pression ramenée au niveau de la mer (hPa)</h3>
                    <div class="ukmog-chart" data-ukmog-chart-pressure></div>
                </article>
                <article class="ukmog-chart-card">
                    <h3 data-ukmog-chart-title-rain>Diagramme précipitations (mm)</h3>
                    <p class="ukmog-chart-total" data-ukmog-rain-total>Précipitations cumulées : —</p>
                    <div class="ukmog-chart" data-ukmog-chart-rain></div>
                </article>
                <article class="ukmog-chart-card">
                    <h3 data-ukmog-chart-title-wind>Diagramme rafales et vent moyen</h3>
                    <div class="ukmog-chart" data-ukmog-chart-wind></div>
                </article>
            </section>
        </div>

        <div class="ukmog-panel" data-ukmog-panel="storms" hidden>
            <p class="ukmog-storm-summary" data-ukmog-storm-summary>
                Diagnostic convectif UKMO Global 10 km : chargement…
            </p>
            <div class="ukmog-top-scroll" data-ukmog-top-scroll="storms" aria-label="Navigation horizontale du tableau orages" hidden><div></div></div>
            <div class="ukmog-table-wrap ukmog-storm-wrap" data-ukmog-scroll-wrap="storms" role="region" aria-label="Prévisions horaires d'orages" tabindex="0">
                <table class="ukmog-table ukmog-storm-table">
                    <thead>
                        <tr>
                            <th scope="col">Date</th>
                            <th scope="col">Heure</th>
                            <th scope="col">Risque orage</th>
                            <th scope="col">CAPE</th>
                            <th scope="col">LCL estimé</th>
                            <th scope="col">Foudre</th>
                            <th scope="col">Grêle</th>
                            <th scope="col">Pluie conv.</th>
                            <th scope="col">Graupel</th>
                            <th scope="col">Pluie 1 h</th>
                            <th scope="col">Rafales</th>
                            <th scope="col">Type</th>
                            <th scope="col">Détails</th>
                        </tr>
                    </thead>
                    <tbody data-ukmog-body-storms>
                        <tr>
                            <td colspan="13" class="ukmog-loading">Chargement du diagnostic orageux…</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="ukmog-storm-note">
                <strong>Version 1.0.0 :</strong> les paramètres convectifs ne sont pas encore intégrés ; ils sont affichés par un tiret.
            </p>
        </div>

        <div class="ukmog-panel" data-ukmog-panel="snow" hidden>
            <p class="ukmog-snow-summary" data-ukmog-snow-summary>
                Diagnostic neige UKMO Global 10 km : chargement…
            </p>
            <div class="ukmog-top-scroll" data-ukmog-top-scroll="snow" aria-label="Navigation horizontale du tableau neige" hidden><div></div></div>
            <div class="ukmog-table-wrap ukmog-snow-wrap" data-ukmog-scroll-wrap="snow" role="region" aria-label="Risque horaire de neige" tabindex="0">
                <table class="ukmog-table ukmog-snow-table">
                    <thead>
                        <tr>
                            <th scope="col">Date</th>
                            <th scope="col">Heure</th>
                            <th scope="col">Risque neige</th>
                            <th scope="col">Phase</th>
                            <th scope="col">Neige 1 h</th>
                            <th scope="col">Neige 3 h</th>
                            <th scope="col">Neige 6 h</th>
                            <th scope="col">Tenue</th>
                            <th scope="col">Pres. hPa</th>
                            <th scope="col">Hum.</th>
                            <th scope="col">Vent moy. / raf.</th>
                            <th scope="col">Cumul neige fraîche</th>
                            <th scope="col">Détails</th>
                        </tr>
                    </thead>
                    <tbody data-ukmog-body-snow>
                        <tr>
                            <td colspan="13" class="ukmog-loading">Chargement du risque de neige…</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="ukmog-snow-note">
                <strong>Version 1.0.0 :</strong> les paramètres neige ne sont pas encore intégrés ; ils sont affichés par un tiret.
            </p>
        </div>

        <footer class="ukmog-footer">
            <span data-ukmog-generated>Mise à jour en cours de lecture…</span>
            <span>
                Données météo directes :
                <a href="https://www.metoffice.gov.uk/services/data/external-data-channels" target="_blank" rel="noopener noreferrer">UKMO Global 10 km — Met Office</a>
                • Recherche des communes :
                <a href="https://geo.api.gouv.fr/decoupage-administratif/communes" target="_blank" rel="noopener noreferrer">API officielle française</a>
                • <a href="https://www.alertes-meteo.com/" target="_blank" rel="noopener noreferrer">www.alertes-meteo.com</a>
            </span>
            <span class="ukmog-plugin-version">Module UKMO Global v<?php echo esc_html(UKMOG_VERSION); ?> (<?php echo esc_html(UKMOG_RELEASE_DATE); ?>)</span>
        </footer>

        <noscript>
            <p class="ukmog-message ukmog-error">JavaScript doit être activé pour rechercher une commune.</p>
        </noscript>
    </section>
    <?php
    return ob_get_clean();
}
