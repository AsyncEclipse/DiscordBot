from PIL import Image


def test_atlantians_ambassador_has_transparent_token_corners():
    with Image.open("images/resources/components/factions/atlantians_ambassador.png") as image:
        assert image.size == (512, 512)
        alpha = image.getchannel("A")
        for corner in [(0, 0), (511, 0), (0, 511), (511, 511)]:
            assert alpha.getpixel(corner) == 0
        assert alpha.getpixel((256, 256)) == 255
