import base64
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


# Mock data - in a real app, this would come from a database
MOCK_POSTS = [
    {
        "id": "post_1",
        "created_at": "2026-02-04T02:13:45Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.instagram.com/p/BSTUMA0Af-M/",
            "canonical_url": "https://www.instagram.com/p/BSTUMA0Af-M/",
            "provider": "instagram"
        },
        "contribution": {
            "translation": {
                "text": "A pear that waits."
            },
            "explanation": {
                "text": "The humor comes from a rhyme in Spanish: \"pera\" (pear) and \"espera\" (waits). The phrase sounds playful because of the similar sounds, and the image shows a pear literally waiting, making the pun visual."
            }
        },
        "engagement": {
            "helpful": 42,
            "confusing": 1
        },
        "author": {
            "id": "user_1",
            "display_name": "spanishpunner"
        }
    },
    {
        "id": "post_2",
        "created_at": "2026-02-04T01:58:02Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://twitter.com/TheSpanishMemes/status/1278446973054595076?lang=en",
            "canonical_url": "https://twitter.com/TheSpanishMemes/status/1278446973054595076",
            "provider": "twitter"
        },
        "contribution": {
            "translation": {
                "text": "When you buy clothes to work out… but you only use them to sleep."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 27,
            "confusing": 0
        },
        "author": {
            "id": "user_2",
            "display_name": "dietadechistes"
        }
    },
    {
        "id": "post_3",
        "created_at": "2026-02-04T01:44:18Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.instagram.com/p/CnofSYrBR7s/",
            "canonical_url": "https://www.instagram.com/p/CnofSYrBR7s/",
            "provider": "instagram"
        },
        "contribution": {
            "translation": {
                "text": "Stop suffering at the gym, here’s the solution."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 35,
            "confusing": 2
        },
        "author": {
            "id": "user_3",
            "display_name": "mañanero"
        }
    },
    {
        "id": "post_4",
        "created_at": "2026-02-04T01:30:44Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.reddit.com/r/SpanishMeme/comments/1qjrpxg/que_cabron/",
            "canonical_url": "https://www.reddit.com/r/SpanishMeme/comments/1qjrpxg/que_cabron/",
            "provider": "reddit"
        },
        "contribution": {
            "translation": {
                "text": "Why are dogs so happy every day? The truth is... we don’t have to go to work."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 19,
            "confusing": 1
        },
        "author": {
            "id": "user_4",
            "display_name": "llegotarde"
        }
    },
    {
        "id": "post_5",
        "created_at": "2026-02-04T01:15:01Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.instagram.com/p/Bqz1gCNj79N/",
            "canonical_url": "https://www.instagram.com/p/Bqz1gCNj79N/",
            "provider": "instagram"
        },
        "contribution": {
            "translation": {
                "text": None
            },
            "explanation": {
                "text": "The joke plays with Spanish numbers: \"dos\" (two), \"tres\" (three), and \"cuatro\" (four), blending them into the English word \"avocados\". The humor comes from visually counting the avocados while changing the word to match the number."
            }
        },
        "engagement": {
            "helpful": 24,
            "confusing": 3
        },
        "author": {
            "id": "user_5",
            "display_name": "juegodepalabras"
        }
    },
    {
        "id": "post_6",
        "created_at": "2026-02-04T01:02:27Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.reddit.com/r/SpanishMeme/comments/1qvnitu/merece_la_pena/",
            "canonical_url": "https://www.reddit.com/r/SpanishMeme/comments/1qvnitu/merece_la_pena/",
            "provider": "reddit"
        },
        "contribution": {
            "translation": {
                "text": "Me going back to sleep because there are still 47 seconds left before my alarm goes off."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 31,
            "confusing": 0
        },
        "author": {
            "id": "user_6",
            "display_name": "nocardio"
        }
    },
    {
        "id": "post_7",
        "created_at": "2026-02-04T00:48:10Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.reddit.com/r/memexico/comments/1qm4qfw/como_la_vida_misma/",
            "canonical_url": "https://www.reddit.com/r/memexico/comments/1qm4qfw/como_la_vida_misma/",
            "provider": "reddit"
        },
        "contribution": {
            "translation": {
                "text": "In the end, being an adult is getting your paycheck, making a coffee, and starting to transfer money."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 22,
            "confusing": 1
        },
        "author": {
            "id": "user_7",
            "display_name": "aprendiendo"
        }
    },
    {
        "id": "post_8",
        "created_at": "2026-02-04T00:33:42Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.instagram.com/p/BJSmjoOD_Vf/",
            "canonical_url": "https://www.instagram.com/p/BJSmjoOD_Vf/",
            "provider": "instagram"
        },
        "contribution": {
            "translation": {
                "text": "Fast food."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 29,
            "confusing": 0
        },
        "author": {
            "id": "user_8",
            "display_name": "insomne"
        }
    },
    {
        "id": "post_9",
        "created_at": "2026-02-04T00:19:03Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.instagram.com/p/CTv-3SZM4R3/",
            "canonical_url": "https://www.instagram.com/p/CTv-3SZM4R3/",
            "provider": "instagram"
        },
        "contribution": {
            "translation": {
                "text": None
            },
            "explanation": {
                "text": "The joke relies on a bilingual pun. In English, the phrase \"it means a lot\" is figurative, while in Spanish \"mucho\" literally means \"a lot.\" The humor comes from using the same phrase in both literal and figurative senses across languages."
            }
        },
        "engagement": {
            "helpful": 26,
            "confusing": 2
        },
        "author": {
            "id": "user_9",
            "display_name": "mamásaben"
        }
    },
    {
        "id": "post_10",
        "created_at": "2026-02-04T00:05:11Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://twitter.com/TheSpanishMemes/status/1175047200134574080",
            "canonical_url": "https://twitter.com/TheSpanishMemes/status/1175047200134574080",
            "provider": "twitter"
        },
        "contribution": {
            "translation": {
                "text": "I'm this close... to going out drinking today."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 33,
            "confusing": 1
        },
        "author": {
            "id": "user_10",
            "display_name": "siempreyo"
        }
    },
    {
        "id": "post_11",
        "created_at": "2026-02-03T23:50:00Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://www.reddit.com/r/SpanishMeme/comments/1qv3213/la_cuesta_de_rafa/",
            "canonical_url": "https://www.reddit.com/r/SpanishMeme/comments/1qv3213/la_cuesta_de_rafa/",
            "provider": "reddit"
        },
        "contribution": {
            "translation": {
                "text": "\"January is finally over.\" January 1st, January 31st."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 15,
            "confusing": 0
        },
        "author": {
            "id": "user_11",
            "display_name": "científico"
        }
    },
    {
        "id": "post_12",
        "created_at": "2026-02-03T23:35:00Z",
        "languages": {
            "source_language_code": "es_ES",
            "target_language_code": "en_US"
        },
        "source": {
            "raw_url": "https://twitter.com/TheSpanishMemes/status/1131165493203787777",
            "canonical_url": "https://twitter.com/TheSpanishMemes/status/1131165493203787777",
            "provider": "twitter"
        },
        "contribution": {
            "translation": {
                "text": "Me when I only talk to you and you take a thousand years to reply."
            },
            "explanation": {
                "text": None
            }
        },
        "engagement": {
            "helpful": 20,
            "confusing": 1
        },
        "author": {
            "id": "user_12",
            "display_name": "cejasaltas"
        }
    },
]


def generate_cursor(post_id, created_at_str):
    cursor_data = {
        "id": post_id,
        "created_at": created_at_str
    }
    cursor_json = json.dumps(cursor_data, sort_keys=True)
    cursor_bytes = cursor_json.encode('utf-8')
    return base64.b64encode(cursor_bytes).decode('utf-8')


def parse_cursor(cursor_str):
    try:
        cursor_bytes = base64.b64decode(cursor_str.encode('utf-8'))
        cursor_json = cursor_bytes.decode('utf-8')
        return json.loads(cursor_json)
    except (ValueError, json.JSONDecodeError):
        return None


class FeedView(APIView):
    """
    API endpoint for fetching feed posts.
    
    Query parameters:
    - limit: Number of posts to return (default: 10)
    - source_language_code: Filter by source language (e.g., "es_ES")
    - target_language_code: Filter by target language (e.g., "en_US")
    - cursor: Pagination cursor (optional)
    """
    
    def get(self, request):
        limit = request.query_params.get('limit', '10')
        try:
            limit = int(limit)
            if limit < 1:
                limit = 10
        except ValueError:
            limit = 10
        
        source_language_code = request.query_params.get('source_language_code')
        target_language_code = request.query_params.get('target_language_code')
        cursor = request.query_params.get('cursor')
        
        # Filter posts by language codes
        filtered_posts = MOCK_POSTS.copy()
        
        if source_language_code:
            filtered_posts = [
                post for post in filtered_posts
                if post['languages']['source_language_code'] == source_language_code
            ]
        
        if target_language_code:
            filtered_posts = [
                post for post in filtered_posts
                if post['languages']['target_language_code'] == target_language_code
            ]
        
        # Handle pagination with cursor
        if cursor:
            cursor_data = parse_cursor(cursor)
            if cursor_data:
                # Find the post with the cursor ID and start from the next one
                cursor_id = cursor_data.get('id')
                cursor_created_at = cursor_data.get('created_at')
                
                # Find the index of the cursor post
                start_index = 0
                for i, post in enumerate(filtered_posts):
                    if post['id'] == cursor_id:
                        start_index = i + 1
                        break
                    # If we can't find exact match, use created_at comparison
                    if post['created_at'] == cursor_created_at:
                        start_index = i + 1
                        break
                
                filtered_posts = filtered_posts[start_index:]
        
        # Get the requested number of posts
        posts = filtered_posts[:limit]
        
        # Determine if there are more posts
        has_more = len(filtered_posts) > limit
        
        # Generate next cursor if there are more posts
        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = generate_cursor(last_post['id'], last_post['created_at'])
        
        # Build applied_filters
        applied_filters = {}
        if source_language_code or target_language_code:
            applied_filters['languages'] = {}
            if source_language_code:
                applied_filters['languages']['source_language_code'] = source_language_code
            if target_language_code:
                applied_filters['languages']['target_language_code'] = target_language_code
        
        # Build response
        response_data = {
            "meta": {
                "limit": limit,
                "has_more": has_more,
                "applied_filters": applied_filters
            },
            "posts": posts
        }
        
        if next_cursor:
            response_data["meta"]["next_cursor"] = next_cursor
        
        return Response(response_data, status=status.HTTP_200_OK)
