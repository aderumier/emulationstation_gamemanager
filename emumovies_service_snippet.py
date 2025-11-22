    def generate_normalized_index(self) -> Dict:
        """
        Generate a normalized index from the EmuMovies database.
        Format: [system][media_type][normalized_filename] = original_filename
        """
        try:
            # Import normalization function
            from game_utils import remove_parentheses
            
            db_file = os.path.join(self.cache_dir, 'emumovies.json')
            if not os.path.exists(db_file):
                logger.error("EmuMovies database not found. Please build it first.")
                return {'success': False, 'error': 'Database not found'}
            
            with open(db_file, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            
            index_data = {}
            
            total_systems = len(db_data)
            logger.info(f"Generating normalized index for {total_systems} systems...")
            
            for system_name, media_types in db_data.items():
                index_data[system_name] = {}
                
                for media_type, media_files in media_types.items():
                    index_data[system_name][media_type] = {}
                    
                    for filename in media_files.keys():
                        # Normalize filename: remove extension, remove parentheses, strip whitespace
                        name_without_ext = os.path.splitext(filename)[0]
                        normalized_name = remove_parentheses(name_without_ext).strip()
                        
                        # Store mapping
                        index_data[system_name][media_type][normalized_name] = filename
            
            # Save index to var/cache/emumovies_index.pl
            cache_dir = 'var/cache'
            os.makedirs(cache_dir, exist_ok=True)
            index_file = os.path.join(cache_dir, 'emumovies_index.pl')
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Normalized index generated successfully: {index_file}")
            
            return {
                'success': True,
                'index_path': index_file,
                'systems_count': len(index_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating normalized index: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

