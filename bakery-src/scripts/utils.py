import hashlib
import json
import sys
import re

import magic
from cnxcommon.urlslug import generate_slug
from .cnx_models import TRANSLUCENT_BINDER_ID, TranslucentBinder
from .profiler import timed
from dateutil import parser, tz
import imagesize

# same as boto3 default chunk size. Don't modify.
BUF_SIZE = 8 * 1024 * 1024

CHARLISTS = {
    "mo_single": (
        "!%&'()*+,-./:;<=>?@[\\]^_z{|}~."
        "\u00a8\u00aa\u00b0\u00b1\u00b2\u00b3\u00b4\u00b7\u00b8"
        "\u00b9\u00ba\u00d7\u00f7\u02c6\u02c7\u02c9\u02ca\u02cb\u02cd\u02d8"
        "\u02d9\u02da\u02dc\u02dd\u02f7\u0302\u0311"
        "\u03f6\u2016\u2018\u2019\u201a\u201b\u201e\u201f"
        "\u2022\u2026\u2032\u2033\u2034\u2035\u2036\u2037\u203e\u2043"
        "\u2044\u2057\u2061\u2062\u2063\u2064\u20db\u20dc"
        "\u2145\u2146\u2190\u2191\u2192\u2193\u2194\u2195\u2196"
        "\u2197\u2198\u2199\u219a\u219b\u219c\u219d\u219e\u219f\u21a0\u21a1"
        "\u21a2\u21a3\u21a4\u21a5\u21a6\u21a7\u21a8\u21a9\u21aa\u21ab\u21ac"
        "\u21ad\u21ae\u21af\u21b0\u21b1\u21b2\u21b3\u21b4\u21b5\u21b6\u21b7"
        "\u21b8\u21b9\u21ba\u21bb\u21bc\u21bd\u21be\u21bf\u21c0\u21c1\u21c2"
        "\u21c3\u21c4\u21c5\u21c6\u21c7\u21c8\u21c9\u21ca\u21cb\u21cc\u21cd"
        "\u21ce\u21cf\u21d0\u21d1\u21d2\u21d3\u21d4\u21d5\u21d6\u21d7\u21d8"
        "\u21d9\u21da\u21db\u21dc\u21dd\u21de\u21df\u21e0\u21e1\u21e2\u21e3"
        "\u21e4\u21e5\u21e6\u21e7\u21e8\u21e9\u21ea\u21eb\u21ec\u21ed\u21ee"
        "\u21ef\u21f0\u21f1\u21f2\u21f3\u21f4\u21f5\u21f6\u21f7\u21f8\u21f9"
        "\u21fa\u21fb\u21fc\u21fd\u21fe\u21ff\u2200\u2201\u2202\u2203\u2204"
        "\u2206\u2207\u2208\u2209\u220a\u220b\u220c\u220d\u220e\u220f"
        "\u2210\u2211\u2212\u2213\u2214\u2215\u2216\u2217\u2218\u2219\u221a"
        "\u221b\u221c\u221d\u221f\u2220\u2221\u2222\u2223\u2224\u2225\u2226"
        "\u2227\u2228\u2229\u222a\u222b\u222c\u222d\u222e\u222f\u2230\u2231"
        "\u2232\u2233\u2234\u2235\u2236\u2237\u2238\u2239\u223a\u223b\u223c"
        "\u223d\u223e\u223f\u2240\u2241\u2242\u2243\u2244\u2245\u2246\u2247"
        "\u2248\u2249\u224a\u224b\u224c\u224d\u224e\u224f\u2250\u2251\u2252"
        "\u2253\u2254\u2255\u2256\u2257\u2258\u2259\u225a\u225b\u225c\u225d"
        "\u225e\u225f\u2260\u2261\u2262\u2263\u2264\u2265\u2266\u2267\u2268"
        "\u2269\u226a\u226b\u226c\u226d\u226e\u226f\u2270\u2271\u2272\u2273"
        "\u2274\u2275\u2276\u2277\u2278\u2279\u227a\u227b\u227c\u227d\u227e"
        "\u227f\u2280\u2281\u2282\u2283\u2284\u2285\u2286\u2287\u2288\u2289"
        "\u228a\u228b\u228c\u228d\u228e\u228f\u2290\u2291\u2292\u2293\u2294"
        "\u2295\u2296\u2297\u2298\u2299\u229a\u229b\u229c\u229d\u229e\u229f"
        "\u22a0\u22a1\u22a2\u22a3\u22a4\u22a5\u22a6\u22a7\u22a8\u22a9\u22aa"
        "\u22ab\u22ac\u22ad\u22ae\u22af\u22b0\u22b1\u22b2\u22b3\u22b4\u22b5"
        "\u22b6\u22b7\u22b8\u22b9\u22ba\u22bb\u22bc\u22bd\u22be\u22bf\u22c0"
        "\u22c1\u22c2\u22c3\u22c4\u22c5\u22c6\u22c7\u22c8\u22c9\u22ca\u22cb"
        "\u22cc\u22cd\u22ce\u22cf\u22d0\u22d1\u22d2\u22d3\u22d4\u22d5\u22d6"
        "\u22d7\u22d8\u22d9\u22da\u22db\u22dc\u22dd\u22de\u22df\u22e0\u22e1"
        "\u22e2\u22e3\u22e4\u22e5\u22e6\u22e7\u22e8\u22e9\u22ea\u22eb\u22ec"
        "\u22ed\u22ee\u22ef\u22f0\u22f1\u22f2\u22f3\u22f4\u22f5\u22f6\u22f7"
        "\u22f8\u22f9\u22fa\u22fb\u22fc\u22fd\u22fe\u22ff\u2308"
        "\u2309\u230a\u230b\u231c\u231d\u2329\u232a\u23b4\u23b5\u23dc\u23dd"
        "\u23de\u23df\u23e0\u23e1\u25a0\u25a1\u25aa\u25ab\u25ad\u25ae"
        "\u25af\u25b0\u25b1\u25b2\u25b3\u25b4\u25b5\u25b6\u25b7\u25b8\u25b9"
        "\u25bc\u25bd\u25be\u25bf\u25c0\u25c1\u25c2\u25c3\u25c4\u25c5\u25c6"
        "\u25c7\u25c8\u25c9\u25cc\u25cd\u25ce\u25cf\u25d6\u25d7"
        "\u25e6\u266d\u266e\u266f\u2758\u2772\u2773\u27e6\u27e7\u27e8"
        "\u27e9\u27ea\u27eb\u27ec\u27ed\u27ee\u27ef\u27f0\u27f1\u27f5\u27f6"
        "\u27f7\u27f8\u27f9\u27fa\u27fb\u27fc\u27fd\u27fe\u27ff\u2900\u2901"
        "\u2902\u2903\u2904\u2905\u2906\u2907\u2908\u2909\u290a\u290b\u290c"
        "\u290d\u290e\u290f\u2910\u2911\u2912\u2913\u2914\u2915\u2916\u2917"
        "\u2918\u2919\u291a\u291b\u291c\u291d\u291e\u291f\u2920\u2921\u2922"
        "\u2923\u2924\u2925\u2926\u2927\u2928\u2929\u292a\u292b\u292c\u292d"
        "\u292e\u292f\u2930\u2931\u2932\u2933\u2934\u2935\u2936\u2937\u2938"
        "\u2939\u293a\u293b\u293c\u293d\u293e\u293f\u2940\u2941\u2942\u2943"
        "\u2944\u2945\u2946\u2947\u2948\u2949\u294a\u294b\u294c\u294d\u294e"
        "\u294f\u2950\u2951\u2952\u2953\u2954\u2955\u2956\u2957\u2958\u2959"
        "\u295a\u295b\u295c\u295d\u295e\u295f\u2960\u2961\u2962\u2963\u2964"
        "\u2965\u2966\u2967\u2968\u2969\u296a\u296b\u296c\u296d\u296e\u296f"
        "\u2970\u2971\u2972\u2973\u2974\u2975\u2976\u2977\u2978\u2979\u297a"
        "\u297b\u297c\u297d\u297e\u297f\u2980\u2981\u2982\u2983\u2984\u2985"
        "\u2986\u2987\u2988\u2989\u298a\u298b\u298c\u298d\u298e\u298f\u2990"
        "\u2991\u2992\u2993\u2994\u2995\u2996\u2997\u2998\u2999\u299a\u299b"
        "\u299c\u299d\u299e\u299f\u29a0\u29a1\u29a2\u29a3\u29a4\u29a5\u29a6"
        "\u29a7\u29a8\u29a9\u29aa\u29ab\u29ac\u29ad\u29ae\u29af\u29b0\u29b1"
        "\u29b2\u29b3\u29b4\u29b5\u29b6\u29b7\u29b8\u29b9\u29ba\u29bb\u29bc"
        "\u29bd\u29be\u29bf\u29c0\u29c1\u29c2\u29c3\u29c4\u29c5\u29c6\u29c7"
        "\u29c8\u29c9\u29ca\u29cb\u29cc\u29cd\u29ce\u29cf\u29d0\u29d1\u29d2"
        "\u29d3\u29d4\u29d5\u29d6\u29d7\u29d8\u29d9\u29db\u29dc\u29dd\u29de"
        "\u29df\u29e0\u29e1\u29e2\u29e3\u29e4\u29e5\u29e6\u29e7\u29e8\u29e9"
        "\u29ea\u29eb\u29ec\u29ed\u29ee\u29ef\u29f0\u29f1\u29f2\u29f3\u29f4"
        "\u29f5\u29f6\u29f7\u29f8\u29f9\u29fa\u29fb\u29fc\u29fd\u29fe\u29ff"
        "\u2a00\u2a01\u2a02\u2a03\u2a04\u2a05\u2a06\u2a07\u2a08\u2a09\u2a0a"
        "\u2a0b\u2a0c\u2a0d\u2a0e\u2a0f\u2a10\u2a11\u2a12\u2a13\u2a14\u2a15"
        "\u2a16\u2a17\u2a18\u2a19\u2a1a\u2a1b\u2a1c\u2a1d\u2a1e\u2a1f\u2a20"
        "\u2a21\u2a22\u2a23\u2a24\u2a25\u2a26\u2a27\u2a28\u2a29\u2a2a\u2a2b"
        "\u2a2c\u2a2d\u2a2e\u2a2f\u2a30\u2a31\u2a32\u2a33\u2a34\u2a35\u2a36"
        "\u2a37\u2a38\u2a39\u2a3a\u2a3b\u2a3c\u2a3d\u2a3e\u2a3f\u2a40\u2a41"
        "\u2a42\u2a43\u2a44\u2a45\u2a46\u2a47\u2a48\u2a49\u2a4a\u2a4b\u2a4c"
        "\u2a4d\u2a4e\u2a4f\u2a50\u2a51\u2a52\u2a53\u2a54\u2a55\u2a56\u2a57"
        "\u2a58\u2a59\u2a5a\u2a5b\u2a5c\u2a5d\u2a5e\u2a5f\u2a60\u2a61\u2a62"
        "\u2a63\u2a64\u2a65\u2a66\u2a67\u2a68\u2a69\u2a6a\u2a6b\u2a6c\u2a6d"
        "\u2a6e\u2a6f\u2a70\u2a71\u2a72\u2a73\u2a74\u2a75\u2a76\u2a77\u2a78"
        "\u2a79\u2a7a\u2a7b\u2a7c\u2a7d\u2a7e\u2a7f\u2a80\u2a81\u2a82\u2a83"
        "\u2a84\u2a85\u2a86\u2a87\u2a88\u2a89\u2a8a\u2a8b\u2a8c\u2a8d\u2a8e"
        "\u2a8f\u2a90\u2a91\u2a92\u2a93\u2a94\u2a95\u2a96\u2a97\u2a98\u2a99"
        "\u2a9a\u2a9b\u2a9c\u2a9d\u2a9e\u2a9f\u2aa0\u2aa1\u2aa2\u2aa3\u2aa4"
        "\u2aa5\u2aa6\u2aa7\u2aa8\u2aa9\u2aaa\u2aab\u2aac\u2aad\u2aae\u2aaf"
        "\u2ab0\u2ab1\u2ab2\u2ab3\u2ab4\u2ab5\u2ab6\u2ab7\u2ab8\u2ab9\u2aba"
        "\u2abb\u2abc\u2abd\u2abe\u2abf\u2ac0\u2ac1\u2ac2\u2ac3\u2ac4\u2ac5"
        "\u2ac6\u2ac7\u2ac8\u2ac9\u2aca\u2acb\u2acc\u2acd\u2ace\u2acf\u2ad0"
        "\u2ad1\u2ad2\u2ad3\u2ad4\u2ad5\u2ad6\u2ad7\u2ad8\u2ad9\u2ada\u2adb"
        "\u2add\u2ade\u2adf\u2ae0\u2ae1\u2ae2\u2ae3\u2ae4\u2ae5\u2ae6\u2ae7"
        "\u2ae8\u2ae9\u2aea\u2aeb\u2aec\u2aed\u2aee\u2aef\u2af0\u2af1\u2af2"
        "\u2af3\u2af4\u2af5\u2af6\u2af7\u2af8\u2af9\u2afa\u2afb\u2afc\u2afd"
        "\u2afe\u2aff\u2b45\u2b46\ufe37\ufe38\u2013"
    ),
    "mo_multi": [
        "!!", "!=", "&&", "**", "*=", "++", "+=", "--", "-=", "->", "..",
        "...", "//", "/=", ":=", "<=", "<>", "==", ">=", "||", "|||",
        "\u223d\u0331", "\u2282\u20d2", "\u2283\u20d2"
    ],
    "mi_blacklist": (
        "\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\u0008\u000e\u000f"
        "\u0010\u0011\u0012\u0013\u0014\u0015\u0016\u0017\u0018\u0019\u001a"
        "\u001b\u001c\u001d\u001e\u001f\u0022\u0060\u007f\u0338\u201c\u201d"
    )
}


@timed
def unformatted_rex_links(doc):
    external_link_elems = doc.xpath(
        '//x:a[@href and starts-with(@href, "./")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    return external_link_elems


# https://stackoverflow.com/a/22058673/756056
@timed
def get_checksums(filename):
    """ generate SHA1 and S3 MD5 etag checksums from file """
    sha1 = hashlib.sha1()
    md5s = []
    try:
        with open(filename, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha1.update(data)
                md5s.append(hashlib.md5(data))
        # chunked calculation for AWS S3 MD5 etag
        # https://stackoverflow.com/a/43819225/756056
        #
        # AWS needs the MD5 quoted inside the string json value.
        # Despite looking like a mistake, this is correct behavior.
        if len(md5s) < 1:
            s3_md5 = '"{}"'.format(
                hashlib.md5().hexdigest())  # pragma: no cover
        elif len(md5s) == 1:
            s3_md5 = '"{}"'.format(md5s[0].hexdigest())
        else:  # pragma: no cover
            digests = b''.join(m.digest() for m in md5s)
            digests_md5 = hashlib.md5(digests)
            s3_md5 = '"{}-{}"'.format(digests_md5.hexdigest(), len(md5s))
        return sha1.hexdigest(), s3_md5
    except IOError:  # file does not exist
        return None, None


@timed
def get_mime_type(filename):
    """ get MIME type of file with libmagic """
    mime_type = ''
    try:
        mime_type = magic.from_file(filename, mime=True)
    finally:
        return mime_type


# Returns (-1, -1) if not an image
def get_size(filename):
    """ get width and height of file with imagesize """
    width = -1
    height = -1
    try:
        width, height = imagesize.get(filename)
    finally:
        return int(width), int(height)


# Based upon amend_tree_with_slugs from cnx-publishing
# (https://github.com/openstax/cnx-publishing/blob/master/cnxpublishing/utils.py#L64)
@timed
def amend_tree_with_slugs(tree, title_seq=[]):
    """Recursively walk through tree and add slug fields"""
    title_seq = title_seq + [tree['title']]
    tree['slug'] = generate_slug(*title_seq)
    if 'contents' in tree:
        for node in tree['contents']:
            amend_tree_with_slugs(node, title_seq)


# Based upon model_to_tree from cnx-epub
# (https://github.com/openstax/cnx-epub/blob/master/cnxepub/models.py#L108)
@timed
def model_to_tree(model, title=None, lucent_id=TRANSLUCENT_BINDER_ID):
    """Given an model, build the tree::
        {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}
    """
    id = model.ident_hash
    if id is None and isinstance(model, TranslucentBinder):
        id = lucent_id  # pragma: no cover
    md = model.metadata
    title = title is not None and title or md.get('title')
    tree = {'id': id, 'title': title}
    if 'data-toc-type' in md:  # pragma: no cover
        tree['toc_type'] = md['data-toc-type']
    if 'data-toc-target-type' in md:  # pragma: no cover
        tree['toc_target_type'] = md['data-toc-target-type']
    if hasattr(model, '__iter__'):
        contents = tree['contents'] = []
        for node in model:
            item = model_to_tree(node, model.get_title_for_node(node),
                                 lucent_id=lucent_id)
            contents.append(item)
    amend_tree_with_slugs(tree)
    return tree


@timed
def parse_uri(uri):  # pragma: no cover
    if not uri.startswith('col', 0, 3):
        return None
    legacy_id, legacy_version = uri.split('@')
    return legacy_id, legacy_version


@timed
def ensure_isoformat(timestamp):
    """Given a timestsamp string either validate it is already ISO8601 and
    return or attempt to convert it.
    """
    try:
        # Using dateutil.parser here instead of datetime.fromisoformat as the
        # former seems to be more robust and avoids some false negatives seen
        # with the latter (e.g. with "2021-03-22T14:14:33.17588-05:00")
        parser.isoparse(timestamp)
        return timestamp
    except ValueError:
        # The provided timestamp needs to be converted
        pass

    # Try parsing timezone separately to catch cases like 'GMT-5' and
    # 'US/Central'
    #
    # Note: We're attempting this before dateutil.parser.parse because if we
    # don't cases like GMT-5 will end up as offset +5:00
    # (see https://github.com/dateutil/dateutil/issues/70)
    try:
        timestamp_notz, timestamp_tz = timestamp.rsplit(' ', 1)
        parsed_tz = tz.gettz(timestamp_tz)
        # The parsed timezone may be None (e.g. for '-0500')
        if parsed_tz:
            return parser.parse(timestamp_notz).replace(tzinfo=parsed_tz).isoformat()
    except ValueError:
        pass

    # Final attempt with just dateutil parser
    try:
        return parser.parse(timestamp).isoformat()
    except ValueError:
        pass

    raise Exception(f"Could not convert non ISO8601 timestamp: {timestamp}")


@timed
def create_json_metadata(output_dir, sha1, mime_type, s3_md5, original_name, width, height):
    """ Create json with MIME type and other metadata of resource file """
    data = {}
    data['original_name'] = original_name
    data['mime_type'] = mime_type
    data['s3_md5'] = s3_md5
    data['sha1'] = sha1
    data['width'] = width
    data['height'] = height
    json_file = output_dir / f'{sha1}.json'
    with json_file.open(mode='w') as outfile:
        json.dump(data, outfile)


@timed
def patch_math_for_pandoc(doc, math_el_namespace):
    """Patch MathML as needed for the conversion process used for gdocs"""

    # It seems texmath used by pandoc has issues when the mathvariant
    # attribute value of "bold-italic" is used with <mtext>, but these convert
    # okay when the element is <mi>.
    for node in doc.xpath(
        '//x:mtext[@mathvariant="bold-italic"]',
        namespaces={"x": math_el_namespace}
    ):
        node.tag = f"{{{math_el_namespace}}}mi"

    # Pandoc renders StarMath annotation
    # which is btw out of specification of MathML.
    # The following lines removes all annotation-xml nodes.
    for node in doc.xpath(
        '//x:annotation-xml[ancestor::x:math]',
        namespaces={"x": math_el_namespace}
    ):
        node.getparent().remove(node)
    # remove also all annotation nodes which can confuse Pandoc
    for node in doc.xpath(
        '//x:annotation[ancestor::x:math]', namespaces={"x": math_el_namespace}
    ):
        node.getparent().remove(node)

    # MathJax 3.x behaves different than legacy MathJax 2.7.x on msubsup MathML.
    # If msubsup has fewer than 3 elements MathJax 3.x does not convert it to
    # msub itself anymore. We are keeping sure in this step that all msubsup
    # with fewer elements than 3 are converted to msub.
    # Pandoc is also confused by msubsup with elements fewer than 3.
    for node in doc.xpath(
        '//x:msubsup[count(*) < 3]', namespaces={"x": math_el_namespace}
    ):
        node.tag = f"{{{math_el_namespace}}}msub"

    # Pandoc's handles math operators more strictly than we expected. Use
    # a whitelist formed from https://github.com/jgm/texmath
    # Readers/TeX/Commands.hs and Readers/MathML/MMLDict.hs
    # Convert mo tags that contain invalid operators into other tags
    for node in doc.xpath('//x:mo', namespaces={"x": math_el_namespace}):
        if node.text is not None:
            # https://www.w3.org/Math/draft-spec/chapter2.html#fund.collapse
            # NOTE: do not trim \xa0 (&nbsp;). It causes issues for mo tags
            text = node.text.strip("\x20\x09\x0d\x0a")
            text_len = len(text)
            if not ((text_len == 1 and text in CHARLISTS["mo_single"]) or
                    (text_len > 1 and text in CHARLISTS["mo_multi"])):
                if text_len == 0:
                    node_type = "mtext"
                else:
                    is_negative = False
                    if text[0] in "-\u2013\u2212" and text_len > 1:
                        text = text[1:]
                        text_len = len(text)
                        is_negative = True

                    if all(s.isnumeric() for s in re.split("[,.]", text)):
                        node_type = "mn"
                    elif (not is_negative and (
                            # Prefer mtext for whitespace where possible
                            text == "\xa0" or
                            # Prefer mtext for content like '___'
                            (text_len >= 3 and
                             all(c == text[0] for c in text)))):
                        node_type = "mtext"
                    elif not any(char in text
                                 for char in CHARLISTS["mi_blacklist"]):
                        node_type = "mi"
                    else:
                        # mtext last resort: problematic characters include
                        # \u2001, \u2003, \u2004, \u2005, \u200a, and \u200b
                        node_type = "mtext"

                log_text = node.text.replace("\n", "\\n")
                print(
                    f'Converting mo to {node_type}: "{log_text}"',
                    file=sys.stderr
                )
                node.tag = f"{{{math_el_namespace}}}{node_type}"

    # Pandoc converts \u0338 to \not{}. This causes problems in mi and mn tags.
    # Convert to mtext.
    for node in doc.xpath(
        (
            '//x:mi[contains(text(), "\u0338")] |'
            '//x:mn[contains(text(), "\u0338")]'
        ),
        namespaces={"x": math_el_namespace}
    ):
        print("Found \\u0338 in math: converting to mtext", file=sys.stderr)
        node.tag = f"{{{math_el_namespace}}}mtext"
