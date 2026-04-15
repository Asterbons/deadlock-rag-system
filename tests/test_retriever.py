from src.rag.retriever import retrieve, format_context

def main():
    # Test 1: hero query
    print("Running Test 1: Hero query (filtered to hero collection)...")
    results = retrieve('hero with fire damage over time', collections=['hero'], top_k=3)
    found_heroes = [r['metadata'].get('hero') for r in results]
    assert any(h == 'hero_inferno' for h in found_heroes), \
        f'Infernus not found for fire damage query. Found: {found_heroes}'
    print('Test 1 passed: fire damage → Infernus found')

    # Test 2: item query
    print("\nRunning Test 2: Item-only search...")
    results = retrieve('spirit power damage item', collections=['item'], top_k=3)
    assert len(results) > 0, "No item results"
    assert all(r['type'] == 'item' for r in results), \
        f"Non-item results found: {[r['type'] for r in results]}"
    print('Test 2 passed: item-only search works')

    # Test 3: score threshold
    print("\nRunning Test 3: Score threshold check...")
    results = retrieve('Mystic Shot', top_k=3)
    if results:
        print(f"Top result: {results[0]['type'].upper()} ({results[0]['metadata'].get('name')}) score: {results[0]['score']:.3f}")
        assert results[0]['score'] > 0.5, \
            f'Top result score too low: {results[0]["score"]}'
        print('Test 3 passed')
    else:
        print('Test 3 skipped: no results')

    # Test 4: format_context output
    print("\nRunning Test 4: format_context check...")
    results = retrieve('Infernus', collections=['hero'], top_k=2)
    ctx = format_context(results)
    assert '===' in ctx
    assert 'score' in ctx
    print('Test 4 passed: format_context output is correct')

    print('\nAll retriever tests passed')

if __name__ == "__main__":
    main()
