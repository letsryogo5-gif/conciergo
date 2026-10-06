from app.models import ModelCourse

SAMPLE_MODEL_COURSES = [
    ModelCourse(
        id="setouchi-udon-towel-yaki",
        title="香川・愛媛を巡る、さぬきうどん名店と今治タオル・三津浜焼き堪能ルート",
        description="朝は香川でコシのあるさぬきうどん、午後は今治でタオルのものづくりに触れ、夕暮れは松山・三津浜で地元のソウルフードを。瀬戸内の食と手仕事をたどるサンプルコースです。",
        region="香川・愛媛",
        creator="瀬戸内よりみち旅",
        image_url="/sample-media/sanuki-udon.svg",
        spot_ids=[
            "kagawa-sanuki-udon",
            "imabari-towel-museum",
            "matsuyama-mitsuhama-yaki",
        ],
        likes=128,
    ),
]
